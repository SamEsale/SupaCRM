#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3000}"
PYTHON_JSON="${PYTHON_JSON:-$ROOT_DIR/backend/.venv313/bin/python}"

if [[ ! -x "$PYTHON_JSON" ]]; then
  PYTHON_JSON="${PYTHON_JSON_FALLBACK:-python3}"
fi

echo "==> Checking backend health"
curl -fsS "$BACKEND_URL/health"
printf "\n"

echo "==> Checking backend readiness"
curl -fsS "$BACKEND_URL/ready"
printf "\n"

echo "==> Checking frontend login page"
curl -fsSI "$FRONTEND_URL/login" >/dev/null
echo "frontend login page is reachable"

if [[ -n "${SMOKE_EMAIL:-}" && -n "${SMOKE_PASSWORD:-}" ]]; then
  echo "==> Checking auth login"
  if [[ -n "${SMOKE_TENANT_ID:-}" ]]; then
    LOGIN_PAYLOAD="{\"tenant_id\":\"${SMOKE_TENANT_ID}\",\"email\":\"${SMOKE_EMAIL}\",\"password\":\"${SMOKE_PASSWORD}\"}"
  else
    LOGIN_PAYLOAD="{\"email\":\"${SMOKE_EMAIL}\",\"password\":\"${SMOKE_PASSWORD}\"}"
  fi

  LOGIN_RESPONSE="$(curl -fsS \
    -H 'Content-Type: application/json' \
    -d "$LOGIN_PAYLOAD" \
    "$BACKEND_URL/auth/login")"

  ACCESS_TOKEN="$(printf '%s' "$LOGIN_RESPONSE" | "$PYTHON_JSON" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
  TENANT_ID="$(printf '%s' "$LOGIN_RESPONSE" | "$PYTHON_JSON" -c 'import json,sys; print(json.load(sys.stdin)["tenant_id"])')"

  echo "==> Checking whoami"
  curl -fsS \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "X-Tenant-Id: $TENANT_ID" \
    "$BACKEND_URL/auth/whoami"
  printf "\n"
fi

cat <<EOF
==> Manual browser QA targets
- $FRONTEND_URL/dashboard
- $FRONTEND_URL/deals
- $FRONTEND_URL/finance/quotes
- $FRONTEND_URL/finance/invoices
- $FRONTEND_URL/finance/payments
- $FRONTEND_URL/support
- $FRONTEND_URL/marketing/campaigns
- $FRONTEND_URL/settings/company
EOF

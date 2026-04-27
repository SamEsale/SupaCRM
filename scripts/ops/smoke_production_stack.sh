#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_JSON="${PYTHON_JSON:-$ROOT_DIR/backend/.venv313/bin/python}"
BASE_URL="${BASE_URL:-http://127.0.0.1}"
API_BASE_URL="${API_BASE_URL:-$BASE_URL/api}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<EOF
Usage: bash scripts/ops/smoke_production_stack.sh

Checks the prod-like stack through the public edge.

Optional environment variables:
  BASE_URL=http://127.0.0.1
  API_BASE_URL=http://127.0.0.1/api
  BOOTSTRAP_API_KEY=...
  BOOTSTRAP_TENANT_ID=...
  BOOTSTRAP_TENANT_NAME=...
  BOOTSTRAP_ADMIN_EMAIL=...
  BOOTSTRAP_ADMIN_PASSWORD=...
  BOOTSTRAP_ADMIN_FULL_NAME=...
  SMOKE_EMAIL=...
  SMOKE_PASSWORD=...
  SMOKE_TENANT_ID=...
EOF
  exit 0
fi

if [[ ! -x "$PYTHON_JSON" ]]; then
  PYTHON_JSON="${PYTHON_JSON_FALLBACK:-python3}"
fi

echo "==> Checking edge health"
curl -fsS "$BASE_URL/health"
printf "\n"

echo "==> Checking edge readiness"
curl -fsS "$BASE_URL/ready"
printf "\n"

echo "==> Checking login page"
curl -fsSI "$BASE_URL/login" >/dev/null
echo "login page is reachable"

if [[ -n "${BOOTSTRAP_API_KEY:-}" && -n "${BOOTSTRAP_TENANT_ID:-}" && -n "${BOOTSTRAP_TENANT_NAME:-}" && -n "${BOOTSTRAP_ADMIN_EMAIL:-}" && -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
  echo "==> Bootstrapping tenant/admin"
  BOOTSTRAP_PAYLOAD="$(cat <<EOF
{"tenant_id":"$BOOTSTRAP_TENANT_ID","tenant_name":"$BOOTSTRAP_TENANT_NAME","admin_email":"$BOOTSTRAP_ADMIN_EMAIL","admin_full_name":"${BOOTSTRAP_ADMIN_FULL_NAME:-First Admin}","admin_password":"$BOOTSTRAP_ADMIN_PASSWORD"}
EOF
)"
  curl -fsS \
    -H 'Content-Type: application/json' \
    -H "X-Bootstrap-Key: $BOOTSTRAP_API_KEY" \
    -d "$BOOTSTRAP_PAYLOAD" \
    "$API_BASE_URL/internal/bootstrap/tenants/bootstrap"
  printf "\n"
fi

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
    "$API_BASE_URL/auth/login")"

  ACCESS_TOKEN="$(printf '%s' "$LOGIN_RESPONSE" | "$PYTHON_JSON" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
  TENANT_ID="$(printf '%s' "$LOGIN_RESPONSE" | "$PYTHON_JSON" -c 'import json,sys; print(json.load(sys.stdin)["tenant_id"])')"

  echo "==> Checking whoami"
  curl -fsS \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "X-Tenant-Id: $TENANT_ID" \
    "$API_BASE_URL/auth/whoami"
  printf "\n"

  echo "==> Checking deals API"
  curl -fsS \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "X-Tenant-Id: $TENANT_ID" \
    "$API_BASE_URL/sales/deals?limit=1" >/dev/null
  echo "deals API is reachable"

  echo "==> Checking invoices API"
  curl -fsS \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "X-Tenant-Id: $TENANT_ID" \
    "$API_BASE_URL/invoices?limit=1" >/dev/null
  echo "invoices API is reachable"
fi

cat <<EOF
==> Manual browser QA targets
- $BASE_URL/login
- $BASE_URL/dashboard
- $BASE_URL/deals
- $BASE_URL/finance/quotes
- $BASE_URL/finance/invoices
- $BASE_URL/finance/payments
- $BASE_URL/support
- $BASE_URL/marketing/campaigns
- $BASE_URL/settings/company
EOF

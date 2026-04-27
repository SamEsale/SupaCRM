#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infrastructure/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infrastructure/.env.production}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<EOF
Usage: bash scripts/ops/validate_production_compose.sh

Validates docker-compose.prod.yml against the intended production env file.

Environment overrides:
  COMPOSE_FILE=/absolute/path/to/docker-compose.prod.yml
  ENV_FILE=/absolute/path/to/.env.production
EOF
  exit 0
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: missing production env file: $ENV_FILE" >&2
  echo "Create it with: bash scripts/ops/init_production_env.sh" >&2
  exit 1
fi

PLACEHOLDER_LINES="$(grep -E '^[A-Z0-9_]+=.*(REPLACE_WITH_REAL_|example\.com)' "$ENV_FILE" || true)"

if [[ -n "$PLACEHOLDER_LINES" ]]; then
  echo "WARNING: $ENV_FILE still contains placeholder values." >&2
  echo "These must be replaced before launch:" >&2
  echo "$PLACEHOLDER_LINES" >&2
  echo >&2
fi

MINIO_ROOT_USER_VALUE="$(grep -E '^MINIO_ROOT_USER=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true)"
MINIO_ROOT_PASSWORD_VALUE="$(grep -E '^MINIO_ROOT_PASSWORD=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true)"
MINIO_ACCESS_KEY_VALUE="$(grep -E '^MINIO_ACCESS_KEY=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true)"
MINIO_SECRET_KEY_VALUE="$(grep -E '^MINIO_SECRET_KEY=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true)"

if [[ -n "$MINIO_ACCESS_KEY_VALUE" || -n "$MINIO_SECRET_KEY_VALUE" ]]; then
  if [[ -z "$MINIO_ACCESS_KEY_VALUE" || -z "$MINIO_SECRET_KEY_VALUE" ]]; then
    echo "ERROR: MINIO_ACCESS_KEY and MINIO_SECRET_KEY must either both be blank or both be set." >&2
    exit 1
  fi

  if [[ "$MINIO_ACCESS_KEY_VALUE" != "$MINIO_ROOT_USER_VALUE" || "$MINIO_SECRET_KEY_VALUE" != "$MINIO_ROOT_PASSWORD_VALUE" ]]; then
    echo "ERROR: the current prod compose flow does not provision a separate MinIO app user." >&2
    echo "Set MINIO_ACCESS_KEY / MINIO_SECRET_KEY blank to reuse the root user," >&2
    echo "or keep them identical to MINIO_ROOT_USER / MINIO_ROOT_PASSWORD." >&2
    exit 1
  fi
fi

echo "==> Validating production compose config"
SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null

echo "==> Compose config is valid for:"
echo "  COMPOSE_FILE=$COMPOSE_FILE"
echo "  ENV_FILE=$ENV_FILE"

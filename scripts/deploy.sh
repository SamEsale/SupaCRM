#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infrastructure/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infrastructure/.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: missing production env file: $ENV_FILE" >&2
  echo "Create it from infrastructure/.env.production.example" >&2
  exit 1
fi

PLACEHOLDER_LINES="$(grep -E '^[A-Z0-9_]+=.*(REPLACE_WITH_REAL_|example\.com)' "$ENV_FILE" || true)"
if [[ -n "$PLACEHOLDER_LINES" ]]; then
  echo "ERROR: production env file still contains placeholder values:" >&2
  echo "$PLACEHOLDER_LINES" >&2
  echo "Replace them before running deploy." >&2
  exit 1
fi

bash "$ROOT_DIR/scripts/ops/validate_production_compose.sh"

echo "==> Starting postgres, redis, and minio"
SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d postgres redis minio

echo "==> Running database migrations"
SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm migrate

echo "==> Building and starting backend, worker, frontend, and nginx"
SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build backend worker frontend nginx

echo "==> Production stack is deploying"
echo "Next checks:"
echo "  curl -fsS http://127.0.0.1/health"
echo "  curl -fsS http://127.0.0.1/ready"
echo "  docker compose -f infrastructure/docker-compose.prod.yml ps"
echo "  curl -X POST http://127.0.0.1/api/internal/bootstrap/tenants/bootstrap ..."
echo "  bash scripts/ops/smoke_production_stack.sh"

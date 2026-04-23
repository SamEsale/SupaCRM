#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.rls.yml"
GRANTS_SQL="$BACKEND_DIR/scripts/grant_rls_test_privileges.sql"

export DATABASE_URL_ADMIN_ASYNC="postgresql+asyncpg://postgres:postgres@localhost:5432/supacrm"
export DATABASE_URL_ASYNC="postgresql+asyncpg://postgres:postgres@localhost:5432/supacrm"
export APP_USER_DSN="postgresql://supacrm_app:supacrm_app@localhost:5432/supacrm"

echo "==> Starting local PostgreSQL for RLS verification..."
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Waiting for PostgreSQL health check..."
for i in {1..60}; do
  if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres -d supacrm >/dev/null 2>&1; then
    echo "PostgreSQL is ready."
    break
  fi
  sleep 2
done

if ! docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres -d supacrm >/dev/null 2>&1; then
  echo "ERROR: PostgreSQL did not become ready."
  exit 1
fi

echo "==> Running Alembic migrations..."
cd "$BACKEND_DIR"
../.venv/bin/alembic upgrade head

echo "==> Granting privileges to non-BYPASSRLS app role..."
docker compose -f "$COMPOSE_FILE" exec -T postgres psql \
  -U postgres \
  -d supacrm \
  -v ON_ERROR_STOP=1 \
  -f /dev/stdin < "$GRANTS_SQL"

echo "==> Verifying app role flags..."
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d supacrm -Atc "
SELECT
  rolname || ' | superuser=' || rolsuper || ' | bypassrls=' || rolbypassrls
FROM pg_roles
WHERE rolname = 'supacrm_app';
"

echo "==> Running DB-backed RLS verification suite..."
cd "$ROOT_DIR"
./.venv/bin/python -m pytest -q backend/tests/integration/test_rls_business_tables_db.py -rA

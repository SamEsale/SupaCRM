#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infrastructure/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infrastructure/.env.production}"
BACKUP_FILE="${BACKUP_FILE:-${1:-}}"

if [ -z "$BACKUP_FILE" ]; then
  echo "USAGE: BACKUP_FILE=/path/to/dump ./scripts/ops/restore_postgres.sh" >&2
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: missing backup file: $BACKUP_FILE" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing production env file: $ENV_FILE" >&2
  echo "Create it with: bash scripts/ops/init_production_env.sh" >&2
  exit 1
fi

if [ -f "${BACKUP_FILE}.sha256" ] && command -v sha256sum >/dev/null 2>&1; then
  (cd "$(dirname "$BACKUP_FILE")" && sha256sum -c "$(basename "$BACKUP_FILE").sha256")
fi

echo "==> Restoring Postgres backup from $BACKUP_FILE"
SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
  set -eu
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pg_restore \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --clean \
    --if-exists \
    --no-owner \
    --exit-on-error
' < "$BACKUP_FILE"

echo "==> Repairing ownership after restore"
SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
  set -eu
  export PGPASSWORD="$POSTGRES_PASSWORD"
  psql \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --set=ON_ERROR_STOP=1 \
    --set=postgres_user="$POSTGRES_USER" \
    --set=admin_user="$DATABASE_ADMIN_USER" \
    --set=db_name="$POSTGRES_DB" \
    --file=/dev/stdin
' < "$ROOT_DIR/scripts/db/reassign_public_ownership.sql"

echo "==> Restore complete"

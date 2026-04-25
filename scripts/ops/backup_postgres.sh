#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infrastructure/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infrastructure/.env.production}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_FILE:-$BACKUP_DIR/supacrm-postgres-$TIMESTAMP.dump}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing production env file: $ENV_FILE" >&2
  echo "Create it with: bash scripts/ops/init_production_env.sh" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

tmp_file="${BACKUP_FILE}.tmp"

echo "==> Writing Postgres backup to $BACKUP_FILE"
SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
  set -eu
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pg_dump \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --format=custom \
    --no-owner \
    --no-acl
' > "$tmp_file"

mv "$tmp_file" "$BACKUP_FILE"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"
fi

if [ -n "${S3_BUCKET:-}" ]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: aws CLI is required when S3_BUCKET is set" >&2
    exit 1
  fi

  echo "==> Copying backup to s3://$S3_BUCKET/postgres/"
  aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/postgres/"
fi

echo "==> Backup complete"
echo "==> Backup file: $BACKUP_FILE"

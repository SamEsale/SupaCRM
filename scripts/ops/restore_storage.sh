#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infrastructure/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infrastructure/.env.production}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/storage}"
FORCE=false
BACKUP_PATH="${BACKUP_PATH:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --force)
      FORCE=true
      ;;
    *)
      BACKUP_PATH="$1"
      ;;
  esac
  shift
done

if [ "$FORCE" != true ]; then
  echo "ERROR: restore_storage.sh requires --force to overwrite the bucket" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing production env file: $ENV_FILE" >&2
  echo "Create it with: bash scripts/ops/init_production_env.sh" >&2
  exit 1
fi

if [ -z "$BACKUP_PATH" ]; then
  BACKUP_PATH="$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
fi

if [ -z "$BACKUP_PATH" ] || [ ! -d "$BACKUP_PATH" ]; then
  echo "ERROR: missing storage backup directory" >&2
  exit 1
fi

case "$BACKUP_PATH" in
  "$BACKUP_DIR"/*)
    CONTAINER_BACKUP_PATH="/backups/storage/${BACKUP_PATH#"$BACKUP_DIR"/}"
    ;;
  *)
    echo "ERROR: BACKUP_PATH must live under $BACKUP_DIR" >&2
    exit 1
    ;;
esac

echo "==> Restoring object storage from $BACKUP_PATH"
MC_CMD=$(cat <<'EOF'
set -eu
MINIO_USER="${MINIO_ROOT_USER:-${MINIO_ACCESS_KEY:-}}"
MINIO_PASSWORD="${MINIO_ROOT_PASSWORD:-${MINIO_SECRET_KEY:-}}"

if [ -z "${MINIO_ENDPOINT:-}" ] || [ -z "${MINIO_BUCKET:-}" ]; then
  echo "ERROR: MINIO_ENDPOINT and MINIO_BUCKET must be set" >&2
  exit 1
fi
if [ -z "$MINIO_USER" ] || [ -z "$MINIO_PASSWORD" ]; then
  echo "ERROR: MinIO credentials are missing" >&2
  exit 1
fi

mc alias set local "$MINIO_ENDPOINT" "$MINIO_USER" "$MINIO_PASSWORD" >/dev/null
mc mb --ignore-existing "local/$MINIO_BUCKET" >/dev/null
mc mirror --overwrite --remove "$BACKUP_PATH" "local/$MINIO_BUCKET"
EOF
)

SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm --no-deps \
  -e FORCE="$FORCE" \
  -e BACKUP_PATH="$CONTAINER_BACKUP_PATH" \
  storage-cli "$MC_CMD"

echo "==> Object storage restore complete"

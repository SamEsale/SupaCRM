#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infrastructure/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infrastructure/.env.production}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/storage}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_NAME="${BACKUP_NAME:-supacrm-storage-$TIMESTAMP}"
BACKUP_PATH="${BACKUP_PATH:-$BACKUP_DIR/$BACKUP_NAME}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing production env file: $ENV_FILE" >&2
  echo "Create it with: bash scripts/ops/init_production_env.sh" >&2
  exit 1
fi

mkdir -p "$BACKUP_PATH"

echo "==> Writing object storage backup to $BACKUP_PATH"
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
rm -rf "$BACKUP_PATH"
mkdir -p "$BACKUP_PATH"
mc mirror --overwrite "local/$MINIO_BUCKET" "$BACKUP_PATH"
cat > "$BACKUP_PATH/.snapshot.json" <<SNAPSHOT
{"created_at":"$TIMESTAMP","bucket":"$MINIO_BUCKET","source":"$MINIO_ENDPOINT"}
SNAPSHOT
EOF
)

SUPACRM_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm --no-deps \
  -e BACKUP_PATH="/backups/storage/$BACKUP_NAME" \
  -e TIMESTAMP="$TIMESTAMP" \
  storage-cli "$MC_CMD"

echo "==> Object storage backup complete"
echo "==> Backup path: $BACKUP_PATH"

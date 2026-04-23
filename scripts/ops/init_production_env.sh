#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE_FILE="${TEMPLATE_FILE:-$ROOT_DIR/infrastructure/.env.production.example}"
TARGET_FILE="${TARGET_FILE:-$ROOT_DIR/infrastructure/.env.production}"
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      cat <<EOF
Usage: bash scripts/ops/init_production_env.sh [--force]

Creates infrastructure/.env.production from infrastructure/.env.production.example.

Environment overrides:
  TEMPLATE_FILE=/absolute/path/to/template
  TARGET_FILE=/absolute/path/to/output
EOF
      exit 0
      ;;
    --force)
      FORCE=true
      ;;
    *)
      echo "USAGE: bash scripts/ops/init_production_env.sh [--force]" >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "ERROR: missing template file: $TEMPLATE_FILE" >&2
  exit 1
fi

if [[ -f "$TARGET_FILE" && "$FORCE" != true ]]; then
  echo "ERROR: target file already exists: $TARGET_FILE" >&2
  echo "Use --force to overwrite it intentionally." >&2
  exit 1
fi

cp "$TEMPLATE_FILE" "$TARGET_FILE"
chmod 600 "$TARGET_FILE"

echo "==> Created production env file: $TARGET_FILE"
echo "==> Replace these placeholder patterns before launch:"
echo "  - every value containing REPLACE_WITH_REAL_"
echo "  - every *.example.com URL"
echo "  - keep MINIO_ACCESS_KEY / MINIO_SECRET_KEY blank unless you provision"
echo "    a separate MinIO app user outside this compose flow"
echo
echo "Next steps:"
echo "1. Edit $TARGET_FILE"
echo "2. Validate compose with: bash scripts/ops/validate_production_compose.sh"
echo "3. Deploy with: bash scripts/deploy.sh"

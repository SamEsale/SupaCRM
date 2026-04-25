#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ ! -f "$ROOT_DIR/.env.supa" ]]; then
  echo "ERROR: missing local env file: $ROOT_DIR/.env.supa" >&2
  exit 1
fi

if [[ ! -x "$ROOT_DIR/backend/.venv313/bin/uvicorn" ]]; then
  echo "ERROR: backend virtualenv is missing. Expected $ROOT_DIR/backend/.venv313/bin/uvicorn" >&2
  exit 1
fi

cd "$ROOT_DIR/backend"
export DEBUG="${DEBUG:-false}"
exec ./.venv313/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}"

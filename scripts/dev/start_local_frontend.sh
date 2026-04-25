#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ ! -f "$FRONTEND_DIR/.env.local" && -z "${NEXT_PUBLIC_API_BASE_URL:-}" ]]; then
  echo "ERROR: missing frontend/.env.local and NEXT_PUBLIC_API_BASE_URL is not set." >&2
  echo "Create frontend/.env.local from frontend/.env.local.example" >&2
  exit 1
fi

cd "$FRONTEND_DIR"
exec npm run dev -- --hostname 127.0.0.1 --port "${PORT:-3000}"

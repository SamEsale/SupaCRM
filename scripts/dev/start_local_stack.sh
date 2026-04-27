#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infrastructure/docker-compose.yml}"

echo "==> Starting local Postgres, Redis, and MinIO"
docker compose -f "$COMPOSE_FILE" up -d postgres redis minio

echo "==> Waiting for services"
docker compose -f "$COMPOSE_FILE" ps

cat <<'EOF'

Local dependency endpoints:
- Postgres: localhost:5432
- Redis: localhost:6379
- MinIO API: http://127.0.0.1:9000
- MinIO Console: http://127.0.0.1:9001

Next steps:
1. backend: bash scripts/dev/start_local_backend.sh
2. frontend: bash scripts/dev/start_local_frontend.sh
3. bootstrap operator: ./backend/.venv313/bin/python scripts/dev/bootstrap_local_operator.py --tenant-id supacrm-test --tenant-name "SupaCRM Test" --admin-email admin@example.com --admin-password 'AdminTest123!'
EOF

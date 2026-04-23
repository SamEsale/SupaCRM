#!/usr/bin/env sh
set -eu

cd /app
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --log-level "$(printf '%s' "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')" \
    --no-access-log \
    --proxy-headers \
    --forwarded-allow-ips='*'

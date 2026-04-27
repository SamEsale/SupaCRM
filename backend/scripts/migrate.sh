#!/usr/bin/env sh
set -eu

cd /app
exec alembic upgrade head

#!/usr/bin/env bash
set -euo pipefail

echo "Checking backend health..."
curl -fsS http://127.0.0.1:8000/health >/dev/null

echo "Checking backend readiness..."
curl -fsS http://127.0.0.1:8000/ready >/dev/null

echo "Testing operator login..."
LOGIN_RESPONSE="$(curl -fsS -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"supacrm@test.com","password":"AdminTest123!"}')"

echo "$LOGIN_RESPONSE" | grep -q "access_token"

echo "Login OK"

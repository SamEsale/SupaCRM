# Local Startup Runbook

This is the canonical local startup path for SupaCRM.

## Prerequisites

- Docker with `docker compose`
- Backend virtualenv at `backend/.venv313`
- Frontend dependencies installed in `frontend/node_modules`

## 1. Prepare env files

```bash
cp .env.supa.example .env.supa
cp frontend/.env.local.example frontend/.env.local
```

Local defaults:

- backend: `http://127.0.0.1:8000`
- frontend: `http://127.0.0.1:3000`
- postgres: `127.0.0.1:5432`
- redis: `127.0.0.1:6379`
- minio api: `127.0.0.1:9000`
- minio console: `127.0.0.1:9001`

## 2. Start dependencies

```bash
bash scripts/dev/start_local_stack.sh
```

This starts the repo's local dependency stack from [`infrastructure/docker-compose.yml`](/Users/samesale/Desktop/SupaCRM/infrastructure/docker-compose.yml):

- postgres
- redis
- minio

## 3. Start the backend

```bash
bash scripts/dev/start_local_backend.sh
```

Notes:

- the backend loads `.env.supa` automatically
- dev startup runs migrations and database init during application startup
- the backend listens on `127.0.0.1:8000`

## 4. Start the frontend

In a second terminal:

```bash
bash scripts/dev/start_local_frontend.sh
```

The frontend listens on `127.0.0.1:3000`.

## 5. Bootstrap the first tenant and admin

Use the real internal bootstrap API through the helper:

```bash
./backend/.venv313/bin/python scripts/dev/bootstrap_local_operator.py \
  --tenant-id supacrm-test \
  --tenant-name "SupaCRM Test" \
  --admin-email admin@example.com \
  --admin-password 'AdminTest123!'
```

This reuses [`/internal/bootstrap/tenants/bootstrap`](/Users/samesale/Desktop/SupaCRM/backend/app/internal/bootstrap_routes.py), not a second onboarding path.

## 6. Validate the local stack

```bash
SMOKE_EMAIL=admin@example.com \
SMOKE_PASSWORD='AdminTest123!' \
bash scripts/dev/smoke_local_launch.sh
```

The smoke helper checks:

- backend `/health`
- backend `/ready`
- frontend `/login`
- optional login and `/auth/whoami` when credentials are supplied

## 7. Manual browser QA targets

- `http://127.0.0.1:3000/dashboard`
- `http://127.0.0.1:3000/deals`
- `http://127.0.0.1:3000/finance/quotes`
- `http://127.0.0.1:3000/finance/invoices`
- `http://127.0.0.1:3000/finance/payments`
- `http://127.0.0.1:3000/support`
- `http://127.0.0.1:3000/marketing/campaigns`
- `http://127.0.0.1:3000/settings/company`

## Common failure cases

- `/ready` fails:
  - check postgres, redis, and minio are running
  - check migrations are at head
  - check `.env.supa` matches the local ports
- frontend loads but API calls fail:
  - check `frontend/.env.local`
  - confirm `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`
- bootstrap helper fails:
  - confirm backend is running
  - confirm `BOOTSTRAP_API_KEY` in `.env.supa`

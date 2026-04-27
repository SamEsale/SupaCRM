# Deployment Runbook

This runbook describes the real prod-like deployment path grounded in the current repository.

## Production shape

- `postgres` holds the primary database.
- `redis` backs queues and background jobs.
- `minio` provides the object-storage layer and backup target.
- `backend` runs FastAPI under `uvicorn`.
- `worker` runs RQ jobs for background cache warmup / invalidation.
- `frontend` runs Next.js in standalone production mode.
- `nginx` is the public edge and proxies `/api` to the backend.

See [`launch_readiness.md`](launch_readiness.md) for the final launch checklist.

## Required environment file

Create `infrastructure/.env.production` from `infrastructure/.env.production.example`.

Recommended command:

```bash
bash scripts/ops/init_production_env.sh
```

This creates the operator-owned env file in the exact location the repo expects.

It must provide:

- `DATABASE_URL_SYNC` and `DATABASE_URL_ADMIN_SYNC` for migrations/bootstrap
- `DATABASE_URL_ASYNC` and `DATABASE_URL_ADMIN_ASYNC` for runtime/admin access
- `DATABASE_APP_USER` and `DATABASE_APP_PASSWORD`
- `DATABASE_ADMIN_USER` and `DATABASE_ADMIN_PASSWORD`
- `REDIS_URL`
- `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`
- `MINIO_BUCKET`
- Optional `S3_BUCKET` / `AWS_*` settings for off-site backup copy
- `JWT_SECRET` and `REFRESH_TOKEN_SECRET`
- `NEXT_PUBLIC_API_BASE_URL=/api`

For the current prod-like compose flow, leave `MINIO_ACCESS_KEY` and
`MINIO_SECRET_KEY` blank unless you have explicitly provisioned a separate
MinIO app user outside this repo flow. By default, the backend uses
`MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`.

Required values must be replaced before launch:

- every `REPLACE_WITH_REAL_*` placeholder
- every `*.example.com` URL

`infrastructure/.env.production.example` is only a template. It is not safe to use unchanged.

Optional file-based secret injection is supported for the critical values above by setting `*_FILE`
variables that point at mounted secret files, for example:

- `JWT_SECRET_FILE=/run/supacrm-secrets/jwt_secret`
- `REFRESH_TOKEN_SECRET_FILE=/run/supacrm-secrets/refresh_token_secret`
- `BOOTSTRAP_API_KEY_FILE=/run/supacrm-secrets/bootstrap_api_key`
- `DATABASE_URL_ASYNC_FILE=/run/supacrm-secrets/database_url_async`

Direct environment variables still take precedence when both are present.

## Compose validation

Validate the prod-like compose file against the intended env file with:

```bash
bash scripts/ops/validate_production_compose.sh
```

This checks the real `docker-compose.prod.yml` render path, warns if placeholder
values remain in the env file, and rejects unsupported MinIO credential splits.

## Deployment order

1. Start database, Redis, and MinIO.
2. Run Alembic migrations as the admin DSN.
3. Start backend, worker, frontend, and nginx.

Recommended command:

```bash
bash scripts/deploy.sh
```

`deploy.sh` now:

- refuses to run if `infrastructure/.env.production` is missing
- refuses to run if placeholder values remain
- validates compose first
- starts dependencies
- runs migrations
- starts backend, worker, frontend, and nginx

Then confirm service state:

```bash
docker compose -f infrastructure/docker-compose.prod.yml ps
curl -fsS http://127.0.0.1/health
curl -fsS http://127.0.0.1/ready
```

`/ready` is meaningful. It verifies:

- application database connectivity
- admin database connectivity
- Alembic revision is at head
- Redis connectivity
- MinIO/storage connectivity when storage is configured

## First-tenant bootstrap

After the stack is healthy, create the first tenant and admin through the real internal bootstrap path proxied by nginx:

```bash
curl -X POST http://127.0.0.1/api/internal/bootstrap/tenants/bootstrap \
  -H 'Content-Type: application/json' \
  -H 'X-Bootstrap-Key: <BOOTSTRAP_API_KEY>' \
  --data '{
    "tenant_id": "supacrm-prod",
    "tenant_name": "SupaCRM Production",
    "admin_email": "admin@example.com",
    "admin_full_name": "First Admin",
    "admin_password": "replace-with-a-real-password"
  }'
```

## Post-deploy smoke checks

Use the helper:

```bash
bash scripts/ops/smoke_production_stack.sh
```

It verifies:

- edge `/health`
- edge `/ready`
- frontend `/login`
- optional bootstrap flow when bootstrap env vars are supplied
- optional login + `whoami` + deals/invoices API checks when credentials are supplied

Then validate manually:

- `GET /health`
- `GET /ready`
- frontend `/login`
- admin login
- dashboard load
- deals list
- quotes list
- invoices list
- payments list
- settings/company
- support list
- marketing campaigns

## Health and readiness

- `/health` is a simple process health signal.
- `/ready` checks database, Redis, Alembic head state, and storage connectivity when configured.

## Scaling layer

The current performance foundation uses Redis-backed auth cache snapshots:

- protected requests use a short-lived principal cache keyed by access-token `jti`
- `/auth/whoami` uses a short-lived profile cache keyed by tenant/user
- login/refresh enqueue cache warmup jobs
- logout and password reset invalidate the affected cache entries

The worker service consumes these jobs from Redis through RQ.

## Edge security baseline

The current nginx edge layer enforces:

- basic request-size limits
- auth-route request method restrictions
- auth-route edge rate limiting compatible with backend auth protections
- simple suspicious URI filtering for path traversal patterns
- proxy header forwarding for `X-Forwarded-Proto`, `X-Forwarded-Port`, and `X-Request-ID`

See [`edge_security.md`](edge_security.md) for the production edge baseline and the future CDN/WAF handoff plan.

## Notes

- Production startup should use `scripts/deploy.sh` plus the checklist in [`launch_readiness.md`](launch_readiness.md).
- Schema changes must be delivered through Alembic migrations.

# Local Login Runbook

This runbook covers the simplest manual login flow for local development.

For the auth/tenant trust model that underpins this flow, see [Auth and Tenant Context Model](../architecture/auth_tenant_model.md).

## Required Environment

- `.env.supa` at the repo root must be present and contain the local dev tenant/admin credentials.
- `frontend/.env.local` must point `NEXT_PUBLIC_API_BASE_URL` at the local backend, usually `http://127.0.0.1:8000`.
- The canonical local stack should be running:
  - Postgres on `127.0.0.1:5432`
  - Redis on `127.0.0.1:6379`
  - MinIO on `127.0.0.1:9000`

Start it with:

```bash
bash scripts/dev/start_local_stack.sh
```

## Start Backend

From the repo root:

```bash
scripts/dev/start_local_backend.sh
```

The helper loads `.env.supa`, sets `DEBUG=false`, and starts the backend on `127.0.0.1:8000`.

## Start Frontend

From the repo root:

```bash
bash scripts/dev/start_local_frontend.sh
```

The local login page should be available at:

```text
http://localhost:3000/login
```

## Bootstrap the Local Admin

Use the operator helper, which calls the real internal bootstrap endpoint with the local bootstrap key from `.env.supa`:

```bash
./backend/.venv313/bin/python scripts/dev/bootstrap_local_operator.py \
  --tenant-id supacrm-test \
  --tenant-name "SupaCRM Test Company" \
  --admin-email supacrm@test.com \
  --admin-password 'AdminTest123!'
```

Direct API equivalent:

```bash
curl -X POST http://127.0.0.1:8000/internal/bootstrap/tenants/bootstrap \
  -H 'Content-Type: application/json' \
  -H 'X-Bootstrap-Key: <BOOTSTRAP_API_KEY>' \
  --data '{
    "tenant_id": "supacrm-test",
    "tenant_name": "SupaCRM Test Company",
    "admin_email": "supacrm@test.com",
    "admin_full_name": "supacrm",
    "admin_password": "AdminTest123!"
  }'
```

## Local Login Flow

- Open `http://localhost:3000/login`
- Enter:
  - Email: `supacrm@test.com`
  - Password: `AdminTest123!`
- On localhost, the tenant field is not required.
- The backend resolves the tenant automatically when the email belongs to exactly one active tenant.
- After login, the frontend stores the resolved `tenant_id` and continues the authenticated session normally.
- On subsequent requests, the frontend uses the authenticated user's stored `tenant_id` as the canonical tenant source.

## Dev vs Prod Behavior

- Dev/local:
  - `tenant_id` may be omitted on `/auth/login`
  - the backend infers the tenant from the email when there is exactly one active match
- Production:
  - `tenant_id` remains required
  - ambiguous or missing tenant resolution fails closed

## Known Failure Modes

- If Postgres is down, login will fail at the backend startup or on the auth request.
- If Redis or MinIO is down, `/ready` will fail and the local stack is not considered launch-ready.
- If the same email belongs to more than one active tenant, local login without `tenant_id` will fail with a clear tenant-ambiguity error.
- If the frontend points at the wrong API base URL, `/login` will still render but the request will fail.
- If the backend is running with a production env, tenant inference is disabled and the plain local login flow will not work.
- If the login page shows a tenant field on localhost, the request host is likely not `localhost`, `127.0.0.1`, or `::1`.

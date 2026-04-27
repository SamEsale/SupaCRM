# RLS Verification Runbook (Business Tables)

This runbook documents how to execute the DB-backed RLS verification suite added for tenant-facing mounted business tables.

Test file:
- `backend/tests/integration/test_rls_business_tables_db.py`
- `backend/tests/integration/test_rls_additional_tenant_tables_db.py`

Target tables:
- `companies`
- `contacts`
- `deals`
- `quotes`
- `invoices`

## What This Suite Proves

For each target table, the suite verifies under real DB execution:
- `SELECT` isolation by `app.tenant_id`
- `INSERT` `WITH CHECK` enforcement (cross-tenant insert denied)
- `UPDATE` isolation (`UPDATE 0` for other-tenant rows)
- `UPDATE` `WITH CHECK` enforcement (tenant reassignment denied)
- `DELETE` isolation (`DELETE 0` for other-tenant rows)

It also verifies RLS metadata/policy presence:
- `relrowsecurity = true`
- `relforcerowsecurity = true`
- policy exists: `<table>_tenant_isolation`

## Runtime Contract

1. Python dependencies
- `pytest`
- `pytest-asyncio`
- `asyncpg`
- `python-dotenv`

Install minimal dependencies (example):

```bash
python -m pip install pytest pytest-asyncio asyncpg python-dotenv
```

2. Migration state
- DB must be migrated to include the RLS completion migration.
- Required revision in history: `20260405_01_enable_rls_for_tenant_business_tables.py`

Apply migrations:

```bash
cd backend
alembic upgrade head
```

3. Required environment / DSNs
- Admin connection (for setup/cleanup + metadata checks):  
  `DATABASE_URL_ADMIN_ASYNC` or `DATABASE_URL_ASYNC`
- App-user connection (for enforcing RLS checks):  
  `APP_USER_DSN` (recommended)

If `APP_USER_DSN` is not set, test fallback is:
- `postgresql://supacrm_app:supacrm_app@127.0.0.1:5432/supacrm`

Bootstrap the non-bypass RLS app role before running the DB-backed suites:

```bash
psql "$DATABASE_URL_ADMIN_SYNC" \
  -v app_user='supacrm_app' \
  -v app_password='REPLACE_WITH_STRONG_PASSWORD' \
  -v db_name='supacrm' \
  -f scripts/db/bootstrap_rls.sql
```

4. Role expectations
- Admin DSN user must be able to seed and clean fixture rows.
- `APP_USER_DSN` user must be a non-bypass app role:
  - not superuser
  - `rolbypassrls = false`
  - has DML permissions on target tables

Optional check:

```sql
select rolname, rolsuper, rolbypassrls
from pg_roles
where rolname in ('supacrm_app', 'postgres');
```

## Command To Run

From repo root:

```bash
python -m pytest -q backend/tests/integration/test_rls_business_tables_db.py
```

Run both DB-backed suites:

```bash
python -m pytest -q \
  backend/tests/integration/test_rls_business_tables_db.py \
  backend/tests/integration/test_rls_additional_tenant_tables_db.py
```

Run a single table block (example):

```bash
python -m pytest -q backend/tests/integration/test_rls_business_tables_db.py -k companies
```

## How To Interpret Results

- `PASS`: DB-level RLS behavior is verified for covered operations on all target tables.
- `SKIPPED`: environment contract not met (missing DSN, DB unreachable, missing dependency).
- `FAIL`: either RLS policy/config regression, role misconfiguration, or schema/migration mismatch.

## Important Limits

- This verifies the database instance you run against.
- It does not by itself prove another environment is migrated/configured identically until run there too.

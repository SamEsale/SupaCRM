# Tenant Onboarding

This runbook covers the real operator-driven tenant bootstrap path for SupaCRM.

## What onboarding now covers

- Tenant bootstrap through the internal bootstrap API.
- First owner/admin creation.
- Trial subscription startup on the starter commercial plan.
- Tenant activation and recovery state changes.
- Onboarding summary reporting for operators.

## Canonical bootstrap path

Do not create a second onboarding path. Use the internal bootstrap API:

- local helper: [`scripts/dev/bootstrap_local_operator.py`](/Users/samesale/Desktop/SupaCRM/scripts/dev/bootstrap_local_operator.py)
- backend route: [`backend/app/internal/bootstrap_routes.py`](/Users/samesale/Desktop/SupaCRM/backend/app/internal/bootstrap_routes.py)

## Operator flow

1. Confirm the stack is healthy with `/health` and `/ready`.
2. Create or verify the tenant and first admin through the bootstrap API.
3. Confirm the onboarding summary reports `bootstrap_complete=true` and `ready_for_use=true`.
4. Log in as the new admin.
5. Confirm the dashboard and settings pages load.

## Local helper example

```bash
./backend/.venv313/bin/python scripts/dev/bootstrap_local_operator.py \
  --tenant-id supacrm-test \
  --tenant-name "SupaCRM Test" \
  --admin-email admin@example.com \
  --admin-password 'AdminTest123!'
```

## Direct API example

```bash
curl -X POST http://127.0.0.1:8000/internal/bootstrap/tenants/bootstrap \
  -H 'Content-Type: application/json' \
  -H 'X-Bootstrap-Key: <BOOTSTRAP_API_KEY>' \
  --data '{
    "tenant_id": "supacrm-test",
    "tenant_name": "SupaCRM Test",
    "admin_email": "admin@example.com",
    "admin_full_name": "First Admin",
    "admin_password": "replace-with-a-real-password"
  }'
```

## Useful checks

```bash
curl -fsS http://127.0.0.1/health
curl -fsS http://127.0.0.1/ready
```

The onboarding summary endpoint should report:

- the tenant status
- first-admin presence
- commercial subscription state
- current plan features
- next recommended action

## Escalation notes

- If bootstrap fails, confirm the bootstrap key and backend reachability first.
- If the tenant is not active, activate the tenant before handing it to users.
- If the first admin is missing, bootstrap again or use the low-level admin helper only as a recovery step.
- If the subscription is suspended or canceled, reactivate the subscription before use.

See [`launch_readiness.md`](launch_readiness.md) for the go-live checklist and [`../customer/getting_started.md`](../customer/getting_started.md) for the customer-facing quick start.

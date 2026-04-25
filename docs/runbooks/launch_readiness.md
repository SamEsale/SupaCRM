# Launch Readiness Checklist

This checklist is the final operator-facing launch guide for the current SupaCRM repository state.

## Launch-scope product surface

SupaCRM currently includes:

- Multi-tenant auth and RBAC
- CRM core for companies and contacts
- Sales and deal-backed leads
- Quotes, invoices, manual payments, accounting, and finance reporting
- Stripe-backed commercial subscriptions, payment-method capture, and webhook event logging
- Marketing settings, WhatsApp-first intake, and campaign drafts
- Support ticketing
- Branding and tenant/operator settings
- Product catalog with media validation
- Backup/restore scripts and prod-like deployment runbooks

The following remain intentionally staged and should not be marketed beyond their current repo support:

- Marketing automation
- Live external WhatsApp provider connectivity
- Full billing portal, dunning, notifications, and non-Stripe subscription automation
- Advanced accounting/tax expansion
- Broad BI/warehouse analytics

## Go-live checklist

1. Confirm environment and dependencies:

- `infrastructure/.env.production` exists and is reviewed
- it was created from `infrastructure/.env.production.example`
- every `REPLACE_WITH_REAL_*` value is replaced
- every `*.example.com` URL is replaced
- secrets are real values, not placeholders
- postgres, redis, minio, backend, worker, frontend, and nginx are up

2. Confirm the stack is healthy:

```bash
curl -fsS http://127.0.0.1/health
curl -fsS http://127.0.0.1/ready
docker compose -f infrastructure/docker-compose.prod.yml ps
```

Also run:

```bash
bash scripts/ops/validate_production_compose.sh
```

3. Confirm database state:

- migrations are at Alembic head
- `/ready` reports `database=ok`

4. Confirm bootstrap/admin setup:

- first tenant exists
- first owner/admin exists
- login succeeds
- dashboard loads

Recommended smoke helper:

```bash
bash scripts/ops/smoke_production_stack.sh
```

5. Confirm recovery basics:

- Postgres backup completes
- storage backup completes
- restore runbook is available and reviewed
- operators know which env file and compose file the recovery scripts use

6. Confirm smoke targets manually in browser:

- login
- dashboard
- deals
- finance quotes
- finance invoices
- finance payments
- settings/company
- support
- marketing campaigns

7. Confirm product-specific browser QA:

- deal create/edit/stage move
- quote create from deal
- invoice create from quote
- payment record on invoice
- settings/company save and reload
- support ticket create/update
- WhatsApp intake submission

8. Confirm operator docs are the current source of truth:

- deployment runbook
- local startup runbook
- tenant onboarding runbook
- backups/restore runbook
- Stripe billing runbook
- production env preparation path

## Operator sign-off

Before a customer is marked live:

- the tenant is active
- the first admin is present and can log in
- launch QA targets have passed
- backups have been exercised
- current repo-supported features have been reviewed
- no unsupported product claims are being made

## Recovery check

If a launch issue occurs, use these runbooks first:

- [`backups_restore.md`](backups_restore.md)
- [`deployment.md`](deployment.md)
- [`stripe_billing.md`](stripe_billing.md)
- [`tenant_onboarding.md`](tenant_onboarding.md)

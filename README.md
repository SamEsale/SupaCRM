# SupaCRM

SupaCRM is a modular, commerce-first SaaS platform with a launch-scope lifecycle of:

`Contacts -> Deals -> Quotes -> Invoices -> Payments -> Accounting -> Reporting`

The product modules are in place. The current repo focus is operational clarity: making local startup, bootstrap, smoke checks, backup/restore, and prod-like deployment reproducible from the repository itself.

## Local Quick Start

1. Prepare env files:

```bash
cp .env.supa.example .env.supa
cp frontend/.env.local.example frontend/.env.local
```

2. Start local dependencies:

```bash
bash scripts/dev/start_local_stack.sh
```

3. Start the backend:

```bash
bash scripts/dev/start_local_backend.sh
```

4. Start the frontend in a second terminal:

```bash
bash scripts/dev/start_local_frontend.sh
```

5. Bootstrap the first tenant and admin through the real internal bootstrap API:

```bash
./backend/.venv313/bin/python scripts/dev/bootstrap_local_operator.py \
  --tenant-id supacrm-test \
  --tenant-name "SupaCRM Test" \
  --admin-email admin@example.com \
  --admin-password 'AdminTest123!'
```

6. Run the local smoke helper:

```bash
SMOKE_EMAIL=admin@example.com \
SMOKE_PASSWORD='AdminTest123!' \
bash scripts/dev/smoke_local_launch.sh
```

Then open [http://127.0.0.1:3000/login](http://127.0.0.1:3000/login).

## Prod-like Deployment Path

1. Create `infrastructure/.env.production` from `infrastructure/.env.production.example`.
2. Start the stack with:

```bash
bash scripts/deploy.sh
```

3. Validate:

```bash
curl -fsS http://127.0.0.1/health
curl -fsS http://127.0.0.1/ready
docker compose -f infrastructure/docker-compose.prod.yml ps
```

4. Bootstrap the first tenant/admin with the internal bootstrap API.
5. Run the launch checklist in [`docs/runbooks/launch_readiness.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/launch_readiness.md).

## Runbooks

- Local startup: [`docs/runbooks/local_startup.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/local_startup.md)
- Local login: [`docs/runbooks/local_login.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/local_login.md)
- Tenant bootstrap/onboarding: [`docs/runbooks/tenant_onboarding.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/tenant_onboarding.md)
- Deployment: [`docs/runbooks/deployment.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/deployment.md)
- Launch checklist: [`docs/runbooks/launch_readiness.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/launch_readiness.md)
- Backups and restore: [`docs/runbooks/backups_restore.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/backups_restore.md)

## Useful Targets

```bash
make help
make local-stack-up
make local-backend
make local-frontend
make smoke-local
make deploy-prod
```

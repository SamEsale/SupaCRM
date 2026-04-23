# Backups and Restore

This runbook covers the real backup and recovery commands currently supported by the repository.

## What is covered now

- Structured JSON application logs to stdout.
- Request-level operational logs with request, tenant, user, path, and timing fields.
- Postgres backup entry point using `pg_dump` from the running production stack.
- Postgres restore entry point using `pg_restore` plus a post-restore ownership repair step so Alembic can run again on the restored stack.
- Object storage backup/restore entry points using the MinIO-compatible `mc mirror` flow.

## Logging and observability

Production services are designed to write to stdout/stderr so container logs remain the primary operational surface.

Useful commands:

```bash
SUPACRM_ENV_FILE=/absolute/path/to/.env.production docker compose --env-file /absolute/path/to/.env.production -f infrastructure/docker-compose.prod.yml ps
docker compose -f infrastructure/docker-compose.prod.yml logs -f backend
docker compose -f infrastructure/docker-compose.prod.yml logs -f frontend
docker compose -f infrastructure/docker-compose.prod.yml logs -f postgres
docker compose -f infrastructure/docker-compose.prod.yml logs -f redis
```

The backend emits structured request logs with:

- `request_id`
- `tenant_id`
- `actor_user_id`
- `user_id`
- `method`
- `path`
- `query`
- `status_code`
- `duration_ms`
- `client_ip`
- `outcome`

## Backup

The supported backup entry point is:

```bash
BACKUP_FILE=backups/supacrm-postgres.dump bash scripts/ops/backup_postgres.sh
```

Behavior:

- Reads `infrastructure/.env.production` by default.
- Can target another validated env file by setting `ENV_FILE=/absolute/path/to/.env.production`.
- Uses the running production Postgres service.
- Writes a custom-format dump file plus an optional `.sha256` checksum file.
- If `S3_BUCKET` is set, copies the dump to `s3://$S3_BUCKET/postgres/` using the AWS CLI.

Object storage backup:

```bash
bash scripts/ops/backup_storage.sh
```

Behavior:

- Mirrors the configured MinIO bucket into `backups/storage/<snapshot>/`.
- Uses the compose-managed `storage-cli` helper and MinIO-compatible `mc mirror`.
- Requires the MinIO service to be running.

Recommended operational checks before backup:

```bash
bash scripts/ops/validate_production_compose.sh
curl -fsS http://127.0.0.1/health
curl -fsS http://127.0.0.1/ready
docker compose -f infrastructure/docker-compose.prod.yml ps
```

Record the backup file path and checksum location in the operator handoff or ticket that triggered the backup.

## Restore

The supported restore entry point is:

```bash
BACKUP_FILE=backups/supacrm-postgres.dump bash scripts/ops/restore_postgres.sh
```

Behavior:

- Verifies the backup checksum when present.
- Restores via `pg_restore --clean --if-exists --no-owner`.
- Reassigns public-schema database objects back to `DATABASE_ADMIN_USER` so migration ownership remains intact.
- Assumes the target Postgres instance is intentionally disposable or already prepared for replacement.
- After a full restore, rerun the deploy/migration step if you restored into a fresh environment.

Object storage restore:

```bash
bash scripts/ops/restore_storage.sh --force
```

Behavior:

- Requires `--force` before any bucket overwrite.
- Mirrors a snapshot directory back into the MinIO bucket with `mc mirror --overwrite --remove`.
- Uses the compose-managed `storage-cli` helper.

Recommended recovery sequence:

```bash
bash scripts/ops/validate_production_compose.sh
BACKUP_FILE=backups/supacrm-postgres.dump bash scripts/ops/restore_postgres.sh
bash scripts/ops/restore_storage.sh --force
bash scripts/deploy.sh
docker compose -f infrastructure/docker-compose.prod.yml ps
curl -fsS http://127.0.0.1/health
curl -fsS http://127.0.0.1/ready
```

## Recovery notes

- Full disaster recovery should restore into a fresh Postgres instance first, then cut traffic over.
- Recovery order:
  1. Stop services.
  2. Restore Postgres.
  3. Reassign ownership.
  4. Restore object storage.
  5. Run migrations.
  6. Start services.
  7. Validate `/health`, `/ready`, auth, and file access.
- Verification checklist:
  - database restored
  - tenant data accessible
  - auth works
  - dashboard loads
  - files accessible
  - logs flowing
- browser QA passes for login, deals, invoices, payments, support, marketing, and settings

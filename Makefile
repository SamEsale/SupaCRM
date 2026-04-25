.PHONY: help local-stack-up local-backend local-frontend smoke-local init-prod-env validate-prod-compose smoke-prod deploy-prod backup-postgres backup-storage

help:
	@echo "Available targets:"
	@echo "  local-stack-up   Start local Postgres, Redis, and MinIO"
	@echo "  local-backend    Start the local backend on 127.0.0.1:8000"
	@echo "  local-frontend   Start the local frontend on 127.0.0.1:3000"
	@echo "  smoke-local      Run local health/readiness/login smoke checks"
	@echo "  init-prod-env    Create infrastructure/.env.production from the example template"
	@echo "  validate-prod-compose  Validate docker-compose.prod.yml with the production env file"
	@echo "  smoke-prod       Run prod-like health/readiness/login smoke checks"
	@echo "  deploy-prod      Run the production-oriented deploy script"
	@echo "  backup-postgres  Run the production Postgres backup script"
	@echo "  backup-storage   Run the object storage backup script"

local-stack-up:
	bash scripts/dev/start_local_stack.sh

local-backend:
	bash scripts/dev/start_local_backend.sh

local-frontend:
	bash scripts/dev/start_local_frontend.sh

smoke-local:
	bash scripts/dev/smoke_local_launch.sh

init-prod-env:
	bash scripts/ops/init_production_env.sh

validate-prod-compose:
	bash scripts/ops/validate_production_compose.sh

smoke-prod:
	bash scripts/ops/smoke_production_stack.sh

deploy-prod:
	bash scripts/deploy.sh

backup-postgres:
	bash scripts/ops/backup_postgres.sh

backup-storage:
	bash scripts/ops/backup_storage.sh

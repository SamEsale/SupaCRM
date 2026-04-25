# SupaCRM Project Structure

Generated: 2026-03-30
Scope: Project tree for `c:\Users\sam.esale\Desktop\SupaCRM`
Excluded: `.git`, `.pytest_cache`, `.vscode`, `venv`, `node_modules`, `__pycache__`, `.next`, `.env.supa`, `.env.local`

```text
SupaCRM
├─ .dockerignore
├─ .editorconfig
├─ .gitignore
├─ CHANGELOG.md
├─ LICENSE
├─ Makefile
├─ PROJECT_STRUCTURE.md
├─ README.md
├─ SUMMARY_OF_CHANGES.md
├─ tree.txt
├─ backend
│  ├─ alembic.ini
│  ├─ check_constraints.sql
│  ├─ check_contacts_columns.sql
│  ├─ Dockerfile
│  ├─ openapi.json
│  ├─ requirements.txt
│  ├─ alembic
│  │  ├─ env.py
│  │  ├─ script.py.mako
│  │  └─ versions
│  │     ├─ 04b3f0195d54_add_tenant_lifecycle_status.py
│  │     ├─ 20260327_01_add_company_id_to_contacts.py
│  │     ├─ 2b82f1d6224c_add_contacts_table.py
│  │     ├─ 3ff6222d94c7_add_user_credentials.py
│  │     ├─ 4df8236cede9_merge_catalog_and_companies_heads.py
│  │     ├─ 542f89e1892a_baseline.py
│  │     ├─ 634ee612c39e_saas_core_schema.py
│  │     ├─ 6c2b5f9a8d13_add_auth_token_state.py
│  │     ├─ 9009424468f8_add_company_address_vat_and_registration_fields.py
│  │     ├─ 9f6f66e8f0a1_add_catalog_products_and_images.py
│  │     ├─ ab3d91f1c2e4_expand_product_image_positions_to_15.py
│  │     ├─ b834d7a56e0d_enable_rls_for_roles_and_tenant_links.py
│  │     ├─ bb602ef6a38b_add_core_constraints.py
│  │     ├─ c9a8e7b4d521_add_deals_table.py
│  │     ├─ d1b4e6f9a211_expand_deal_stages_and_transition_support.py
│  │     └─ f40dbf97675e_add_companies_table.py
│  ├─ app
│  │  ├─ __init__.py
│  │  ├─ api.py
│  │  ├─ db.py
│  │  ├─ db_admin.py
│  │  ├─ db_deps.py
│  │  ├─ logging.py
│  │  ├─ main.py
│  │  ├─ models.py
│  │  ├─ openapi.py
│  │  ├─ accounting
│  │  │  ├─ fx_rates.py
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  └─ service.py
│  │  ├─ admin
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  └─ service.py
│  │  ├─ audit
│  │  │  ├─ __init__.py
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  ├─ service.py
│  │  │  ├─ services.py
│  │  │  └─ utils.py
│  │  ├─ auth
│  │  │  ├─ __init__.py
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  ├─ security.py
│  │  │  └─ service.py
│  │  ├─ catalog
│  │  │  ├─ images.py
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  └─ service.py
│  │  ├─ cli
│  │  │  ├─ __init__.py
│  │  │  ├─ __main__.py
│  │  │  ├─ bootstrap.py
│  │  │  ├─ root.py
│  │  │  ├─ tenant.py
│  │  │  └─ user.py
│  │  ├─ common
│  │  │  ├─ constants.py
│  │  │  ├─ deps.py
│  │  │  ├─ errors.py
│  │  │  ├─ models
│  │  │  │  ├─ base.py
│  │  │  │  └─ mixins.py
│  │  │  └─ schemas
│  │  │     ├─ base.py
│  │  │     └─ errors.py
│  │  ├─ core
│  │  │  ├─ __init__.py
│  │  │  ├─ config.py
│  │  │  ├─ db_urls.py
│  │  │  ├─ env.py
│  │  │  ├─ paths.py
│  │  │  ├─ security.py
│  │  │  ├─ settings.py
│  │  │  ├─ middleware
│  │  │  │  ├─ audit_context.py
│  │  │  │  ├─ rate_limit.py
│  │  │  │  ├─ request_id.py
│  │  │  │  ├─ security_headers.py
│  │  │  │  └─ tenant_middleware.py
│  │  │  ├─ security
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ deps.py
│  │  │  │  ├─ jwt.py
│  │  │  │  ├─ passwords.py
│  │  │  │  └─ rbac.py
│  │  │  └─ utils
│  │  │     ├─ hashing.py
│  │  │     ├─ pagination.py
│  │  │     ├─ time.py
│  │  │     └─ validators.py
│  │  ├─ crm
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  └─ service.py
│  │  ├─ debug
│  │  │  ├─ __init__.py
│  │  │  └─ routes.py
│  │  ├─ integrations
│  │  │  ├─ chat
│  │  │  │  ├─ __init__.py
│  │  │  │  └─ service.py
│  │  │  ├─ email
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ provider.py
│  │  │  │  ├─ service.py
│  │  │  │  └─ templates
│  │  │  ├─ fx_api
│  │  │  │  ├─ __init__.py
│  │  │  │  └─ client.py
│  │  │  ├─ payoneer
│  │  │  ├─ revolut
│  │  │  ├─ storage
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ minio_client.py
│  │  │  │  └─ presign.py
│  │  │  ├─ stripe
│  │  │  │  ├─ __init__.py
│  │  │  │  └─ client.py
│  │  │  └─ whatsapp_business
│  │  │     ├─ __init__.py
│  │  │     ├─ models.py
│  │  │     ├─ routes.py
│  │  │     ├─ schemas.py
│  │  │     └─ service.py
│  │  ├─ internal
│  │  │  ├─ __init__.py
│  │  │  └─ bootstrap_routes.py
│  │  ├─ invoicing
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  └─ service.py
│  │  ├─ marketing
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  ├─ service.py
│  │  │  ├─ whatsapp_integration.py
│  │  │  └─ social_integrations
│  │  ├─ payments
│  │  │  ├─ models.py
│  │  │  ├─ payment_methods.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  ├─ service.py
│  │  │  ├─ subscriptions.py
│  │  │  ├─ gateway
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ base_gateway.py
│  │  │  │  ├─ payoneer_gateway.py
│  │  │  │  ├─ revolut_gateway.py
│  │  │  │  └─ stripe_gateway.py
│  │  │  └─ webhooks
│  │  │     ├─ payoneer_webhook.py
│  │  │     ├─ revolut_webhook.py
│  │  │     └─ stripe_webhook.py
│  │  ├─ rbac
│  │  │  ├─ models.py
│  │  │  ├─ permissions.py
│  │  │  ├─ rbac_seed.py
│  │  │  ├─ schemas.py
│  │  │  └─ service.py
│  │  ├─ reporting
│  │  │  ├─ models.py
│  │  │  ├─ queries.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  ├─ service.py
│  │  │  └─ dashboards
│  │  ├─ sales
│  │  │  ├─ __init__.py
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  ├─ service.py
│  │  │  └─ whatsapp_integration.py
│  │  ├─ support
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  └─ service.py
│  │  ├─ tenants
│  │  │  ├─ membership_models.py
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ schemas.py
│  │  │  └─ service.py
│  │  └─ workers
│  │     ├─ queue.py
│  │     ├─ scheduler.py
│  │     ├─ cron
│  │     └─ tasks
│  │        ├─ email_dispatch.py
│  │        ├─ fx_refresh.py
│  │        ├─ reporting_refresh.py
│  │        └─ webhook_retry.py
│  ├─ scripts
│  │  ├─ create_admin_user.py
│  │  ├─ create_tenant.py
│  │  ├─ fix_alembic_version.py
│  │  ├─ grant_audit_write.py
│  │  ├─ inspect_companies.py
│  │  ├─ inspect_contacts.py
│  │  ├─ inspect_rbac_schema.py
│  │  ├─ inspect_rls_policies.py
│  │  ├─ inspect_tenants.py
│  │  ├─ inspect_user_credentials.py
│  │  ├─ list_tenants.py
│  │  ├─ seed_rbac.py
│  │  ├─ verify_app_user_connection.py
│  │  ├─ verify_bootstrap_result.py
│  │  ├─ verify_bootstrap_rls_as_app_user.py
│  │  ├─ verify_gamma_credentials.py
│  │  ├─ verify_phase_2_2_bootstrap.py
│  │  ├─ verify_phase_2_3_auth.py
│  │  ├─ verify_phase_2_3_inactive_auth_states.py
│  │  ├─ verify_phase_2_4_tenant_route_auth.py
│  │  ├─ verify_phase_2_4_user_role_matrix.py
│  │  ├─ verify_phase_2_5_tenant_lifecycle.py
│  │  ├─ verify_phase_2_6_companies_crud.py
│  │  ├─ verify_phase_2_6_contacts_crud.py
│  │  ├─ verify_rls_db_level.py
│  │  ├─ verify_seed_schema.py
│  │  ├─ verify_user_credentials_count.py
│  │  ├─ verify_user_credentials_table.py
│  │  ├─ dev
│  │  │  ├─ create_admin_user.py
│  │  │  ├─ create_tenant.py
│  │  │  └─ seed_rbac.py
│  │  └─ verify
│  │     ├─ check_phase_2_2.py
│  │     ├─ check_phase_2_4_rbac.py
│  │     └─ check_phase_2_4_roles.p
│  ├─ src
│  │  ├─ constants
│  │  │  └─ auth.ts
│  │  └─ lib
│  │     └─ auth-storage.ts
│  └─ tests
│     ├─ e2e
│     ├─ integration
│     ├─ marketing
│     │  └─ test_marketing.py
│     ├─ sales
│     │  └─ test_sales.py
│     └─ unit
├─ ci-cd
│  └─ pipelines.md
├─ docs
│  ├─ api
│  │  └─ openapi.yaml
│  ├─ architecture
│  │  ├─ data-models.md
│  │  ├─ multi-tenancy-design.md
│  │  └─ system-overview.md
│  ├─ prd
│  ├─ roadmap
│  ├─ runbooks
│  │  ├─ backups_restore.md
│  │  ├─ deployment.md
│  │  ├─ incident_response.md
│  │  ├─ migrations.md
│  │  └─ tenant_onboarding.md
│  └─ srs
├─ frontend
│  ├─ .gitignore
│  ├─ AGENTS.md
│  ├─ CLAUDE.md
│  ├─ eslint.config.mjs
│  ├─ next.config.ts
│  ├─ next-env.d.ts
│  ├─ openapi.json
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ postcss.config.mjs
│  ├─ product-create-test.json
│  ├─ README.md
│  ├─ tsconfig.json
│  ├─ public
│  │  ├─ file.svg
│  │  ├─ globe.svg
│  │  ├─ next.svg
│  │  ├─ vercel.svg
│  │  └─ window.svg
│  └─ src
│     ├─ app
│     │  ├─ favicon.ico
│     │  ├─ globals.css
│     │  ├─ layout.tsx
│     │  ├─ page.tsx
│     │  ├─ (auth)
│     │  │  └─ login
│     │  │     └─ page.tsx
│     │  └─ (dashboard)
│     │     ├─ layout.tsx
│     │     ├─ companies
│     │     │  ├─ page.tsx
│     │     │  └─ create
│     │     │     └─ page.tsx
│     │     ├─ contacts
│     │     │  ├─ page.tsx
│     │     │  └─ create
│     │     │     └─ page.tsx
│     │     ├─ dashboard
│     │     │  └─ page.tsx
│     │     ├─ deals
│     │     │  ├─ page.tsx
│     │     │  └─ create
│     │     │     └─ page.tsx
│     │     └─ products
│     │        ├─ page.tsx
│     │        └─ create
│     │           └─ page.tsx
│     ├─ components
│     │  ├─ auth
│     │  │  ├─ login-form.tsx
│     │  │  ├─ logout-button.tsx
│     │  │  └─ protected-route.tsx
│     │  ├─ crm
│     │  │  ├─ companies-list.tsx
│     │  │  ├─ company-create-form.tsx
│     │  │  ├─ contact-create-form.tsx
│     │  │  └─ contacts-list.tsx
│     │  ├─ deals
│     │  │  ├─ DealCreateForm.tsx
│     │  │  └─ DealsList.tsx
│     │  ├─ layout
│     │  │  └─ dashboard-shell.tsx
│     │  ├─ navigation
│     │  │  ├─ Sidebar.tsx
│     │  │  └─ sidebar-menu.ts
│     │  ├─ products
│     │  │  ├─ EditProductModal.tsx
│     │  │  ├─ ProductCreateForm.tsx
│     │  │  └─ ProductsList.tsx
│     │  └─ ui
│     ├─ constants
│     │  ├─ auth.ts
│     │  └─ env.ts
│     ├─ hooks
│     │  └─ use-auth.ts
│     ├─ lib
│     │  ├─ api-client.ts
│     │  └─ auth-storage.ts
│     ├─ services
│     │  ├─ auth.service.ts
│     │  ├─ companies.service.ts
│     │  ├─ contacts.service.ts
│     │  ├─ deals.service.ts
│     │  └─ products.service.ts
│     ├─ store
│     └─ types
│        ├─ auth.ts
│        ├─ crm.ts
│        └─ product.ts
├─ frontend_vite_backup
│  ├─ Dockerfile
│  ├─ package.json
│  ├─ tsconfig.json
│  ├─ vite.config.ts
│  ├─ public
│  └─ src
│     ├─ App.tsx
│     ├─ api
│     ├─ components
│     ├─ context
│     ├─ hooks
│     ├─ layouts
│     ├─ modules
│     │  ├─ admin
│     │  ├─ auth
│     │  ├─ catalog
│     │  ├─ crm
│     │  ├─ invoicing
│     │  ├─ payments
│     │  ├─ reporting
│     │  └─ support
│     ├─ theme
│     └─ utils
├─ infrastructure
│  ├─ docker-compose.yml
│  ├─ ansible
│  │  ├─ inventories
│  │  └─ playbooks
│  │     └─ deploy_backend.yml
│  ├─ minio
│  ├─ monitoring
│  │  ├─ grafana
│  │  └─ prometheus
│  ├─ nginx
│  │  └─ nginx.conf
│  ├─ postgres
│  │  └─ init.sql
│  ├─ redis
│  └─ terraform
│     └─ modules
│        └─ network
│           └─ README.md
├─ maintenance
│  ├─ BACKLOG.md
│  └─ ADR
├─ scripts
│  ├─ deploy.sh
│  ├─ seed_data.py
│  ├─ db
│  │  ├─ bootstrap_rls.sql
│  │  ├─ create_read_replica_notes.md
│  │  └─ sanity_checks.sql
│  ├─ dev
│  │  ├─ create_admin_user.py
│  │  └─ create_tenant.py
│  └─ maintenance
└─ security
   ├─ data-protection.md
   ├─ dependency-scanning.md
   ├─ rbac-model.md
   ├─ README.md
   ├─ secrets-and-rotation.md
   └─ threat-model.md
```

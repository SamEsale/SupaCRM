\set ON_ERROR_STOP on

-- SupaCRM RLS app-role bootstrap
--
-- Safe usage from psql:
--   psql "$DATABASE_URL_ADMIN_SYNC" \
--     -v app_user='supacrm_app' \
--     -v app_password='REPLACE_WITH_STRONG_PASSWORD' \
--     -v db_name='supacrm' \
--     -f scripts/db/bootstrap_rls.sql
--
-- Defaults:
--   app_user     = supacrm_app
--   app_password = supacrm_app
--   db_name      = supacrm
--
-- This script is idempotent. It does not disable RLS, drop data, or mutate
-- Alembic-managed RLS policies. It only manages the non-bypass application
-- role and the privileges that role needs for tenant-scoped RLS access.

\if :{?app_user}
\else
\set app_user 'supacrm_app'
\endif

\if :{?app_password}
\else
\set app_password 'supacrm_app'
\endif

\if :{?db_name}
\else
\set db_name 'supacrm'
\endif

DO
$$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') THEN
        EXECUTE format(
            'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
            :'app_user',
            :'app_password'
        );
    ELSE
        EXECUTE format(
            'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
            :'app_user',
            :'app_password'
        );
    END IF;
END
$$;

GRANT CONNECT ON DATABASE :"db_name" TO :"app_user";
GRANT USAGE ON SCHEMA public TO :"app_user";

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO :"app_user";

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO :"app_user";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES TO :"app_user";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT
ON SEQUENCES TO :"app_user";

DO
$$
DECLARE
    role_state record;
BEGIN
    SELECT
        rolname,
        rolsuper,
        rolbypassrls
    INTO role_state
    FROM pg_roles
    WHERE rolname = :'app_user';

    IF role_state.rolname IS NULL THEN
        RAISE EXCEPTION 'RLS app role % was not created', :'app_user';
    END IF;

    IF role_state.rolsuper THEN
        RAISE EXCEPTION 'RLS app role % must not be SUPERUSER', :'app_user';
    END IF;

    IF role_state.rolbypassrls THEN
        RAISE EXCEPTION 'RLS app role % must not have BYPASSRLS', :'app_user';
    END IF;
END
$$;

SELECT
    rolname,
    rolsuper,
    rolbypassrls
FROM pg_roles
WHERE rolname = :'app_user';

#!/usr/bin/env sh
set -eu

: "${POSTGRES_USER:?POSTGRES_USER must be set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"
: "${POSTGRES_DB:?POSTGRES_DB must be set}"
: "${DATABASE_ADMIN_USER:?DATABASE_ADMIN_USER must be set}"
: "${DATABASE_ADMIN_PASSWORD:?DATABASE_ADMIN_PASSWORD must be set}"
: "${DATABASE_APP_USER:?DATABASE_APP_USER must be set}"
: "${DATABASE_APP_PASSWORD:?DATABASE_APP_PASSWORD must be set}"

export PGPASSWORD="$POSTGRES_PASSWORD"

psql -v ON_ERROR_STOP=1 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -v db_name="$POSTGRES_DB" \
    -v admin_user="$DATABASE_ADMIN_USER" \
    -v admin_password="$DATABASE_ADMIN_PASSWORD" \
    -v app_user="$DATABASE_APP_USER" \
    -v app_password="$DATABASE_APP_PASSWORD" <<'EOSQL'
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'admin_user') THEN
        format(
            'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS',
            :'admin_user',
            :'admin_password'
        )
    ELSE
        format(
            'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS',
            :'admin_user',
            :'admin_password'
        )
END
\gexec

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') THEN
        format(
            'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
            :'app_user',
            :'app_password'
        )
    ELSE
        format(
            'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
            :'app_user',
            :'app_password'
        )
END
\gexec

ALTER DATABASE :"db_name" OWNER TO :"admin_user";
GRANT CONNECT ON DATABASE :"db_name" TO :"admin_user", :"app_user";
GRANT USAGE ON SCHEMA public TO :"app_user";

ALTER DEFAULT PRIVILEGES FOR ROLE :"admin_user" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_user";

ALTER DEFAULT PRIVILEGES FOR ROLE :"admin_user" IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO :"app_user";
EOSQL

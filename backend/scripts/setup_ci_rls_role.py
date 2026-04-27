from __future__ import annotations

import os
from urllib.parse import urlparse

import psycopg
from psycopg import sql


def _admin_sync_dsn() -> str:
    dsn = (
        os.getenv("DATABASE_URL_ADMIN_SYNC")
        or os.getenv("DATABASE_URL_SYNC")
        or os.getenv("DATABASE_URL")
    )
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL_ADMIN_SYNC or DATABASE_URL_SYNC must be set for CI RLS setup"
        )
    return dsn.replace("postgresql+psycopg://", "postgresql://", 1).replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )


def _database_name(dsn: str) -> str:
    parsed = urlparse(dsn)
    name = parsed.path.lstrip("/")
    if not name:
        raise RuntimeError(f"Unable to determine database name from DSN: {dsn!r}")
    return name


def main() -> None:
    admin_dsn = _admin_sync_dsn()
    db_name = _database_name(admin_dsn)
    app_user = os.getenv("DATABASE_APP_USER", "supacrm_app")
    app_password = os.getenv("DATABASE_APP_PASSWORD", "supacrm_app")

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {role_name}) THEN
                            EXECUTE format(
                                'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
                                {role_name},
                                {role_password}
                            );
                        ELSE
                            EXECUTE format(
                                'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
                                {role_name},
                                {role_password}
                            );
                        END IF;
                    END
                    $$;
                    """
                ).format(
                    role_name=sql.Literal(app_user),
                    role_password=sql.Literal(app_password),
                )
            )

            cur.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {};").format(
                    sql.Identifier(db_name),
                    sql.Identifier(app_user),
                )
            )
            cur.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {};").format(
                    sql.Identifier(app_user),
                )
            )
            cur.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {};"
                ).format(sql.Identifier(app_user))
            )
            cur.execute(
                sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {};").format(
                    sql.Identifier(app_user),
                )
            )
            cur.execute(
                sql.SQL(
                    """
                    ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {};
                    """
                ).format(sql.Identifier(app_user))
            )
            cur.execute(
                sql.SQL(
                    """
                    ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA public
                    GRANT USAGE, SELECT ON SEQUENCES TO {};
                    """
                ).format(sql.Identifier(app_user))
            )
            cur.execute(
                """
                select rolname, rolsuper, rolbypassrls
                from pg_roles
                where rolname = %s
                """,
                (app_user,),
            )
            role_row = cur.fetchone()
            if role_row is None:
                raise RuntimeError(f"App role {app_user!r} was not created")
            rolname, rolsuper, rolbypassrls = role_row
            if rolsuper or rolbypassrls:
                raise RuntimeError(
                    f"App role {rolname!r} is misconfigured: superuser={rolsuper} bypassrls={rolbypassrls}"
                )

    print(f"Configured non-bypass RLS app role {app_user!r} for database {db_name!r}.")


if __name__ == "__main__":
    main()

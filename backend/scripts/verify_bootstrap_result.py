import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


def find_upwards(filename: str, start: Path) -> Path | None:
    cur = start.resolve()
    while True:
        candidate = cur / filename
        if candidate.exists():
            return candidate
        if cur.parent == cur:
            return None
        cur = cur.parent


def main() -> int:
    env_path = find_upwards(".env.supa", Path.cwd())
    if not env_path:
        print("ERROR: Could not find .env.supa by searching upwards from cwd.")
        return 2
    load_dotenv(env_path, override=False)

    dsn = os.getenv("DATABASE_URL_SYNC")
    if not dsn:
        print("ERROR: DATABASE_URL_SYNC not set")
        return 2
    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    tenant_id = os.getenv("VERIFY_TENANT_ID")
    if not tenant_id:
        print("ERROR: set VERIFY_TENANT_ID env var to the tenant_id printed by bootstrap.")
        print('Example: $env:VERIFY_TENANT_ID = "<tenant_uuid>"')
        return 2

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Tenant row (global table)
            cur.execute("select id, name, is_active from tenants where id = %s", (tenant_id,))
            t = cur.fetchone()
            print("tenant:", t)

            # IMPORTANT:
            # You are connecting as DATABASE_URL_SYNC (postgres superuser).
            # Superusers bypass RLS, so relying on set_config('app.tenant_id', ...) will NOT restrict rows.
            # Therefore we explicitly filter by tenant_id for tenant-scoped tables.

            # Tenant-scoped checks (explicit filtering)
            cur.execute("select count(*) as roles from roles where tenant_id = %s", (tenant_id,))
            print("roles:", cur.fetchone()["roles"])

            cur.execute("select name from roles where tenant_id = %s order by name", (tenant_id,))
            print("role names:", [r["name"] for r in cur.fetchall()])

            cur.execute("select count(*) as tenant_users from tenant_users where tenant_id = %s", (tenant_id,))
            print("tenant_users:", cur.fetchone()["tenant_users"])

            cur.execute(
                "select count(*) as tenant_user_roles from tenant_user_roles where tenant_id = %s",
                (tenant_id,),
            )
            print("tenant_user_roles:", cur.fetchone()["tenant_user_roles"])

            # Global permissions (global table)
            cur.execute("select count(*) as permissions from permissions")
            print("permissions:", cur.fetchone()["permissions"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

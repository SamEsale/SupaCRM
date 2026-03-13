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


def must_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"ERROR: {name} is not set")
    return v


def main() -> int:
    env_path = find_upwards(".env.supa", Path.cwd())
    if not env_path:
        print("ERROR: Could not find .env.supa by searching upwards from cwd.")
        return 2
    load_dotenv(env_path, override=False)

    tenant_id = must_env("VERIFY_TENANT_ID")

    # Prefer a dedicated app_user DSN if you have one; otherwise we derive from DATABASE_URL_SYNC
    # You can set APP_USER_DSN explicitly to avoid guessing:
    #   $env:APP_USER_DSN="postgresql://app_user:<pwd>@localhost:5432/supacrm"
    app_user_dsn = os.getenv("APP_USER_DSN")
    if not app_user_dsn:
        print("ERROR: APP_USER_DSN is not set. Set it to your app_user connection string.")
        print('Example: $env:APP_USER_DSN="postgresql://app_user:YOURPASSWORD@localhost:5432/supacrm"')
        return 2

    app_user_dsn = app_user_dsn.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(app_user_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Must set tenant context; otherwise RLS should block tenant tables
            cur.execute("select set_config('app.tenant_id', %s, true)", (tenant_id,))

            cur.execute("select count(*) as roles from roles")
            roles_count = cur.fetchone()["roles"]

            cur.execute("select count(*) as tenant_users from tenant_users")
            tu_count = cur.fetchone()["tenant_users"]

            cur.execute("select count(*) as tur from tenant_user_roles")
            tur_count = cur.fetchone()["tur"]

            print("as app_user with tenant set:")
            print("  roles:", roles_count)
            print("  tenant_users:", tu_count)
            print("  tenant_user_roles:", tur_count)

            # Now test that changing tenant_id changes visibility (should go to 0 for random tenant)
            cur.execute("select set_config('app.tenant_id', %s, true)", ("00000000-0000-0000-0000-000000000000",))
            cur.execute("select count(*) as roles from roles")
            roles_other = cur.fetchone()["roles"]
            print("as app_user with different tenant set:")
            print("  roles:", roles_other)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

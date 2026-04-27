import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


TABLES = [
    "tenants",
    "users",
    "roles",
    "permissions",
    "tenant_users",
    "tenant_user_roles",
    "role_permissions",
]


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
    cwd = Path.cwd()
    print("cwd =", cwd)

    env_path = find_upwards(".env.supa", cwd)
    if not env_path:
        print("ERROR: Could not find .env.supa by searching upwards from cwd.")
        return 2

    print("loading env from:", env_path)
    load_dotenv(env_path, override=False)

    dsn = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    print("DATABASE_URL_SYNC set?", bool(os.getenv("DATABASE_URL_SYNC")))
    print("DATABASE_URL set?", bool(os.getenv("DATABASE_URL")))

    if not dsn:
        print("ERROR: DATABASE_URL_SYNC (or DATABASE_URL) is not set after loading env file.")
        return 2

    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            print("\n== Columns ==")
            cur.execute(
                """
                select table_name, column_name, data_type
                from information_schema.columns
                where table_schema='public'
                  and table_name = any(%s)
                order by table_name, ordinal_position
                """,
                (TABLES,),
            )
            for r in cur.fetchall():
                print(f"{r['table_name']:18} {r['column_name']:22} {r['data_type']}")

            print("\n== Unique constraints ==")
            cur.execute(
                """
                select conrelid::regclass::text as table_name,
                       conname,
                       pg_get_constraintdef(oid) as def
                from pg_constraint
                where contype='u'
                  and connamespace='public'::regnamespace
                  and conrelid::regclass::text = any(%s)
                order by table_name, conname
                """,
                (TABLES,),
            )
            for r in cur.fetchall():
                print(f"{r['table_name']:18} {r['conname']:30} {r['def']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

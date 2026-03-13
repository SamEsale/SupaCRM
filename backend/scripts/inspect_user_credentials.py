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
    if env_path:
        load_dotenv(env_path, override=False)

    dsn = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("ERROR: DATABASE_URL_SYNC (or DATABASE_URL) not set")
    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("select to_regclass('public.user_credentials') as reg")
            print("regclass:", cur.fetchone()["reg"])

            print("\n== Columns ==")
            cur.execute(
                """
                select column_name, data_type, is_nullable, column_default
                from information_schema.columns
                where table_schema='public'
                  and table_name='user_credentials'
                order by ordinal_position
                """
            )
            for r in cur.fetchall():
                print(
                    f"{r['column_name']:16} {r['data_type']:25} "
                    f"nullable={r['is_nullable']:3} default={r['column_default']}"
                )

            print("\n== Constraints ==")
            cur.execute(
                """
                select conname, contype, pg_get_constraintdef(oid) as def
                from pg_constraint
                where conrelid = 'public.user_credentials'::regclass
                order by contype, conname
                """
            )
            for r in cur.fetchall():
                print(f"{r['contype']} {r['conname']}: {r['def']}")

            print("\n== Indexes ==")
            cur.execute(
                """
                select indexname, indexdef
                from pg_indexes
                where schemaname='public'
                  and tablename='user_credentials'
                order by indexname
                """
            )
            for r in cur.fetchall():
                print(f"- {r['indexname']}: {r['indexdef']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

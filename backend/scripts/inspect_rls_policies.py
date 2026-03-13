import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


TABLES = ["roles", "tenant_users", "tenant_user_roles", "audit_logs"]


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
        print("ERROR: DATABASE_URL_SYNC (or DATABASE_URL) not set")
        return 2
    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            print("== RLS enabled / forced ==")
            cur.execute(
                """
                select c.relname,
                       c.relrowsecurity as rls_enabled,
                       c.relforcerowsecurity as rls_forced
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'public'
                  and c.relname = any(%s)
                order by c.relname
                """,
                (TABLES,),
            )
            for r in cur.fetchall():
                print(f"{r['relname']:18} enabled={r['rls_enabled']} forced={r['rls_forced']}")

            print("\n== Policies ==")
            cur.execute(
                """
                select pol.polname,
                       c.relname as table_name,
                       pg_get_expr(pol.polqual, pol.polrelid) as using_expr,
                       pg_get_expr(pol.polwithcheck, pol.polrelid) as withcheck_expr,
                       pol.polcmd,
                       array_to_string(pol.polroles::regrole[], ',') as roles
                from pg_policy pol
                join pg_class c on c.oid = pol.polrelid
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'public'
                  and c.relname = any(%s)
                order by c.relname, pol.polname
                """,
                (TABLES,),
            )
            rows = cur.fetchall()
            if not rows:
                print("(no policies found for these tables)")
            else:
                for p in rows:
                    print(f"- {p['table_name']}.{p['polname']} cmd={p['polcmd']} roles=[{p['roles']}]")
                    print(f"    USING:     {p['using_expr']}")
                    print(f"    WITHCHECK: {p['withcheck_expr']}")

            print("\n== app_user bypass check ==")
            cur.execute(
                """
                select r.rolname,
                       r.rolsuper,
                       r.rolbypassrls
                from pg_roles r
                where r.rolname in ('app_user','postgres')
                order by r.rolname
                """
            )
            for rr in cur.fetchall():
                print(f"{rr['rolname']:10} super={rr['rolsuper']} bypassrls={rr['rolbypassrls']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

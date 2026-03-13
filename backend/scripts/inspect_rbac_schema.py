from app.core.env import load_env_supa
load_env_supa()

import os
from sqlalchemy import create_engine, text

dsn = os.getenv("DATABASE_URL_SYNC")
assert dsn, "Missing DATABASE_URL_SYNC"

tables = [
    ("public", "permissions"),
    ("public", "role_permissions"),
    ("public", "roles"),
    ("public", "tenant_user_roles"),
    ("public", "tenant_users"),
    ("public", "users"),
]

engine = create_engine(dsn)

with engine.connect() as conn:
    print("DSN OK. Inspecting RBAC schema...\n")

    for schema, table in tables:
        exists = conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = :schema AND table_name = :table
                )
            """),
            {"schema": schema, "table": table},
        ).scalar_one()

        print(f"{schema}.{table} exists={exists}")
        if not exists:
            print()
            continue

        cols = conn.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = :table
                ORDER BY ordinal_position
            """),
            {"schema": schema, "table": table},
        ).fetchall()

        for c, t in cols:
            print(f"  - {c}: {t}")
        print()

    print("Sample permissions (up to 20):")
    if conn.execute(text("SELECT to_regclass('public.permissions')")).scalar_one():
        rows = conn.execute(text("SELECT * FROM public.permissions ORDER BY 1 LIMIT 20")).fetchall()
        for r in rows:
            print(" ", r)

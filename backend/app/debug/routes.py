from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_deps import get_auth_db

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/rbac")
async def debug_rbac(db: AsyncSession = Depends(get_auth_db)):
    # Tables we expect in some form
    tables = [
        "permissions",
        "role_permissions",
        "roles",
        "tenant_users",
        "tenant_user_roles",
        "users",
        "user_credentials",
    ]

    out = {"tables": {}, "columns": {}, "samples": {}}

    for t in tables:
        out["tables"][t] = bool((await db.execute(text(f"SELECT to_regclass('public.{t}')"))).scalar_one())

    # Column inventory for key tables (full list)
    for t in ["permissions", "role_permissions", "tenant_user_roles", "roles", "tenant_users"]:
        if not out["tables"].get(t):
            continue
        rows = (await db.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=:t
            ORDER BY ordinal_position
        """), {"t": t})).fetchall()
        out["columns"][t] = [{"name": r[0], "type": r[1]} for r in rows]

    # Samples (first 5 rows)
    for t in ["permissions", "role_permissions", "tenant_user_roles", "roles"]:
        if not out["tables"].get(t):
            continue
        try:
            rows = (await db.execute(text(f"SELECT * FROM public.{t} LIMIT 5"))).fetchall()
            out["samples"][t] = [list(r) for r in rows]
        except Exception as e:
            out["samples"][t] = {"error": str(e)}

    return out

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_deps import get_auth_db
from app.core.security.deps import get_current_user


async def user_has_permission(db: AsyncSession, user_id: str, permission_code: str) -> bool:
    """
    Check if a user has a given permission code via:
      tenant_user_roles -> role_permissions -> permissions(code)

    Assumes tenant scoping is already applied via RLS (app.tenant_id set).
    """
    permission_code = permission_code.strip()

    res = await db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM public.tenant_user_roles tur
                JOIN public.role_permissions rp
                  ON rp.role_id = tur.role_id
                JOIN public.permissions p
                  ON p.id = rp.permission_id
                WHERE tur.user_id = :user_id
                  AND p.code = :perm
            )
            """
        ),
        {"user_id": user_id, "perm": permission_code},
    )
    return bool(res.scalar_one())


def require_permission(permission_code: str) -> Callable:
    """
    FastAPI dependency factory:
      - requires a valid JWT (get_current_user)
      - requires app.tenant_id already set (via auth db dependency)
      - checks RBAC via user_has_permission()
    """
    async def _dep(
        user_id: str = Depends(get_current_user),
        db: AsyncSession = Depends(get_auth_db),
    ) -> bool:
        ok = await user_has_permission(db, str(user_id), permission_code)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_code}",
            )
        return True

    return _dep

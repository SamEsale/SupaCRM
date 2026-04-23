from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.auth_cache import auth_cache, ttl_until_epoch
from app.core.security.jwt import decode_access_token
from app.db import async_session_factory, get_db, set_tenant_guc

security = HTTPBearer(auto_error=False)


async def get_commercial_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = creds.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    header_tenant_id = getattr(request.state, "header_tenant_id", None)
    if header_tenant_id and str(header_tenant_id) != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant mismatch (header tenant does not match token tenant)",
        )

    cached_principal = await auth_cache.get_principal_snapshot(str(payload["jti"]))
    if cached_principal:
        merged = dict(payload)
        merged.update(cached_principal)
        return merged

    async with async_session_factory() as session:
        await set_tenant_guc(session, str(tenant_id))
        result = await session.execute(
            text(
                """
                select
                    t.status as tenant_status,
                    t.is_active as tenant_is_active,
                    u.is_active as user_is_active,
                    tu.is_active as membership_is_active
                from public.tenant_users tu
                join public.users u
                  on u.id = tu.user_id
                join public.tenants t
                  on t.id = tu.tenant_id
                where tu.tenant_id = cast(:tenant_id as varchar)
                  and tu.user_id = cast(:user_id as varchar)
                """
            ),
            {"tenant_id": str(tenant_id), "user_id": str(user_id)},
        )
        row = result.mappings().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated account is inactive",
        )

    if not row["user_is_active"] or not row["membership_is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated account is inactive",
        )

    validated_payload = dict(payload)
    validated_payload["tenant_status"] = row["tenant_status"]
    validated_payload["tenant_is_active"] = bool(row["tenant_is_active"])
    validated_payload["user_is_active"] = bool(row["user_is_active"])
    validated_payload["membership_is_active"] = bool(row["membership_is_active"])

    await auth_cache.set_principal_snapshot(
        str(payload["jti"]),
        validated_payload,
        ttl_seconds=ttl_until_epoch(int(payload["exp"]), maximum_seconds=60),
    )
    return validated_payload


async def get_commercial_db(
    request: Request,
    principal: dict = Depends(get_commercial_principal),
) -> AsyncSession:
    jwt_tenant_id = principal.get("tenant_id")
    if not jwt_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing tenant_id",
        )

    header_tenant_id = getattr(request.state, "header_tenant_id", None)
    if not header_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required tenant header: X-Tenant-Id",
        )

    if str(header_tenant_id) != str(jwt_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant mismatch (header tenant does not match token tenant)",
        )

    request.state.tenant_id = str(jwt_tenant_id)
    async for session in get_db(request, tenant_id=str(jwt_tenant_id)):
        yield session


async def user_has_commercial_permission(db: AsyncSession, user_id: str, permission_code: str) -> bool:
    result = await db.execute(
        text(
            """
            select exists (
                select 1
                from public.tenant_user_roles tur
                join public.role_permissions rp
                  on rp.role_id = tur.role_id
                join public.permissions p
                  on p.id = rp.permission_id
                where tur.user_id = :user_id
                  and p.code = :perm
            )
            """
        ),
        {"user_id": user_id, "perm": permission_code.strip()},
    )
    return bool(result.scalar_one())


def require_commercial_permission(permission_code: str):
    async def _dep(
        principal: dict = Depends(get_commercial_principal),
        db: AsyncSession = Depends(get_commercial_db),
    ) -> bool:
        ok = await user_has_commercial_permission(db, str(principal["sub"]), permission_code)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_code}",
            )
        return True

    return _dep

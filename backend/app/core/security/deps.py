from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.core.security.auth_cache import auth_cache, ttl_until_epoch
from app.core.security.jwt import decode_access_token
from app.db import async_session_factory, set_tenant_guc

security = HTTPBearer(auto_error=False)


async def get_current_principal(
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
        cached_payload = dict(payload)
        cached_payload.update(cached_principal)
        return cached_payload

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

    tenant_status = row["tenant_status"]

    if tenant_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not active. Access has been blocked.",
        )

    if (
        not row["tenant_is_active"]
        or not row["user_is_active"]
        or not row["membership_is_active"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated account is inactive",
        )

    validated_payload = dict(payload)
    validated_payload["tenant_status"] = tenant_status
    validated_payload["tenant_is_active"] = bool(row["tenant_is_active"])
    validated_payload["user_is_active"] = bool(row["user_is_active"])
    validated_payload["membership_is_active"] = bool(row["membership_is_active"])

    await auth_cache.set_principal_snapshot(
        str(payload["jti"]),
        validated_payload,
        ttl_seconds=ttl_until_epoch(int(payload["exp"]), maximum_seconds=60),
    )
    return validated_payload


def get_current_user(payload: dict = Depends(get_current_principal)) -> str:
    """
    Returns the authenticated user id (JWT 'sub').
    This matches how create_access_token() sets subject.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )
    return str(user_id)


def get_current_tenant_id(payload: dict = Depends(get_current_principal)) -> str:
    """
    Returns tenant_id from the JWT payload (used for tenant-scoped authorization).
    """
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing tenant_id",
        )
    return str(tenant_id)


def require_active_tenant(_: dict = Depends(get_current_principal)) -> None:
    """
    Explicit lifecycle dependency for protected routers.

    get_current_principal() already enforces:
    - valid token
    - tenant membership
    - tenant lifecycle
    - active user
    - active membership

    This wrapper exists to make lifecycle gating explicit at router level.
    """
    return None

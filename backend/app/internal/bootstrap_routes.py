from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security.auth_cache import auth_cache
from app.db_admin import get_admin_session
from app.tenants.service import bootstrap_tenant

router = APIRouter(prefix="/internal/bootstrap", tags=["internal-bootstrap"])


class TenantLifecycleUpdateRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    status_reason: str | None = Field(default=None, max_length=255)


class TenantBootstrapRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=64)
    tenant_name: str = Field(..., min_length=1, max_length=255)
    admin_email: str = Field(..., min_length=1, max_length=255)
    admin_full_name: str | None = Field(default=None, max_length=255)
    admin_password: str | None = Field(default=None, min_length=1, max_length=255)


def require_bootstrap_key(x_bootstrap_key: str | None = Header(default=None)) -> None:
    if not x_bootstrap_key or x_bootstrap_key != settings.BOOTSTRAP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bootstrap key",
        )


def _status_to_is_active(status_value: str) -> bool:
    normalized = status_value.strip().lower()
    if normalized == "active":
        return True
    if normalized in {"suspended", "disabled"}:
        return False
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported tenant status: {status_value}",
    )


@router.get("/ping", dependencies=[Depends(require_bootstrap_key)])
async def ping() -> dict:
    return {"ok": True}


@router.get("/db", dependencies=[Depends(require_bootstrap_key)])
async def db_check(admin_session: AsyncSession = Depends(get_admin_session)) -> dict:
    result = await admin_session.execute(text("select 1"))
    return {"db": result.scalar_one()}


@router.patch(
    "/tenants/{tenant_id}/status",
    dependencies=[Depends(require_bootstrap_key)],
)
async def update_tenant_status_internal(
    tenant_id: str,
    payload: TenantLifecycleUpdateRequest,
    admin_session: AsyncSession = Depends(get_admin_session),
) -> dict:
    normalized_status = payload.status.strip().lower()
    effective_reason = payload.status_reason.strip() if payload.status_reason else None
    effective_is_active = _status_to_is_active(normalized_status)

    result = await admin_session.execute(
        text(
            """
            update public.tenants
            set status = cast(:status as varchar),
                status_reason = cast(:status_reason as varchar),
                is_active = :is_active,
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            returning id, name, is_active, status, status_reason, created_at, updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "status": normalized_status,
            "status_reason": effective_reason,
            "is_active": effective_is_active,
        },
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {tenant_id}",
        )

    await admin_session.commit()
    await auth_cache.invalidate_snapshots_for_tenant(tenant_id)

    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "is_active": bool(row["is_active"]),
        "status": str(row["status"]),
        "status_reason": row["status_reason"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.post("/tenants/bootstrap", dependencies=[Depends(require_bootstrap_key)])
async def bootstrap_tenant_internal(
    payload: TenantBootstrapRequest,
    admin_session: AsyncSession = Depends(get_admin_session),
) -> dict:
    async with admin_session.begin():
        result = await bootstrap_tenant(
            admin_session,
            tenant_id=payload.tenant_id,
            tenant_name=payload.tenant_name,
            admin_email=payload.admin_email,
            admin_full_name=payload.admin_full_name,
            admin_password=payload.admin_password,
        )

    await auth_cache.invalidate_snapshots_for_tenant(payload.tenant_id)

    return {
        "tenant": {
            "id": result.tenant.tenant_id,
            "name": payload.tenant_name,
            "created_tenant": result.tenant.created_tenant,
        },
        "rbac": {
            "created_roles": result.rbac.created_roles,
            "created_permissions": result.rbac.created_permissions,
        },
        "admin": {
            "tenant_id": result.admin.tenant_id,
            "user_id": result.admin.user.user_id,
            "email": result.admin.user.email,
            "created_user": result.admin.user.created_user,
            "created_credentials": result.admin.user.created_credentials,
            "password_set": result.admin.user.password_set,
            "assigned_roles": [assignment.role_name for assignment in result.admin.role_assignments],
        },
    }

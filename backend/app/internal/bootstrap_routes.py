from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db_admin import get_admin_session

router = APIRouter(prefix="/internal/bootstrap", tags=["internal-bootstrap"])


class TenantLifecycleUpdateRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    status_reason: str | None = Field(default=None, max_length=255)


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

    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "is_active": bool(row["is_active"]),
        "status": str(row["status"]),
        "status_reason": row["status_reason"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
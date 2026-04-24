from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commercial.deps import get_commercial_db, get_commercial_principal, require_commercial_permission
from app.payments.settings_service import get_payment_provider_foundation
from app.rbac.permissions import PERMISSION_BILLING_ACCESS

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/provider-foundation")
async def get_payment_provider_foundation_route(
    _: bool = Depends(require_commercial_permission(PERMISSION_BILLING_ACCESS)),
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> dict:
    snapshot = await get_payment_provider_foundation(
        db,
        tenant_id=str(principal["tenant_id"]),
    )
    return asdict(snapshot)

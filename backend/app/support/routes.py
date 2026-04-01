from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security.rbac import require_permission
from app.rbac.permissions import PERMISSION_SUPPORT_READ

router = APIRouter(prefix="/support", tags=["support"])


@router.get(
    "/probe",
    dependencies=[Depends(require_permission(PERMISSION_SUPPORT_READ))],
)
async def support_probe() -> dict:
    return {
        "module": "support",
        "permission_required": PERMISSION_SUPPORT_READ,
        "status": "ok",
    }
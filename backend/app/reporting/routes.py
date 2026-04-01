from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security.rbac import require_permission
from app.rbac.permissions import PERMISSION_REPORTING_READ

router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get(
    "/probe",
    dependencies=[Depends(require_permission(PERMISSION_REPORTING_READ))],
)
async def reporting_probe() -> dict:
    return {
        "module": "reporting",
        "permission_required": PERMISSION_REPORTING_READ,
        "status": "ok",
    }
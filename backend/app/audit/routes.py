from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import RecentAuditActivityListResponse, RecentAuditActivityOut
from app.audit.service import list_recent_activity
from app.core.security.deps import get_current_tenant_id
from app.db_deps import get_auth_db
from app.audit.models import AuditLog
from app.core.security.rbac import require_permission

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/test", dependencies=[Depends(require_permission("audit.write"))])
async def audit_test(
    db: AsyncSession = Depends(get_auth_db),
):
    log = AuditLog(
        action="audit.test",
        resource="system",
        message="Audit test executed successfully",
        status_code=200,
    )
    db.add(log)
    return {"ok": True}


@router.get(
    "/recent",
    response_model=RecentAuditActivityListResponse,
)
async def recent_audit_activity_route(
    limit: int = Query(default=10, ge=1, le=50),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> RecentAuditActivityListResponse:
    items = await list_recent_activity(
        db,
        tenant_id=tenant_id,
        limit=limit,
    )
    return RecentAuditActivityListResponse(
        items=[RecentAuditActivityOut(**asdict(item)) for item in items],
        total=len(items),
    )

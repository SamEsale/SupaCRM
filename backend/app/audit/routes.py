from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

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

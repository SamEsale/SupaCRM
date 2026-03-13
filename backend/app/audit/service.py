from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog


class AuditService:
    """
    Best-effort audit logging.

    Rules:
    - Never raise exceptions to callers.
    - Routes/middleware must not write ORM directly.
    - Easy to evolve later to queue/batch/external sink.
    """

    @staticmethod
    async def log(
        *,
        db: AsyncSession,
        tenant_id: str,
        action: str,
        actor_user_id: Optional[str] = None,
        actor_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        status_code: Optional[int] = None,
        message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            entry = AuditLog(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                actor_ip=actor_ip,
                request_id=request_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                status_code=status_code,
                message=message,
                meta=meta,
            )
            db.add(entry)
            await db.commit()
        except Exception as exc:
            logger.warning("Audit write failed (ignored): {}", exc)
            try:
                await db.rollback()
            except Exception:
                pass

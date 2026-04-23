from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog


class AuditService:
    """
    Best-effort audit logging as a transaction participant.

    Rules:
    - If a caller passes an owned DB session, this service must not
      commit/rollback/begin/close that session.
    - Keep writes lightweight and let request-level transaction ownership
      decide final commit/rollback.
    - Do not raise from this helper for add-time failures.
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
        if not tenant_id:
            logger.warning("Audit write skipped: missing tenant_id")
            return

        if not action:
            logger.warning("Audit write skipped: missing action")
            return

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
            # Request-scoped dependency owns transaction boundaries.
        except Exception as exc:
            logger.warning("Audit write failed (ignored): {}", exc)


@dataclass(slots=True)
class RecentAuditActivity:
    id: str
    action: str
    resource: str | None
    resource_id: str | None
    status_code: int | None
    message: str | None
    actor_user_id: str | None
    actor_full_name: str | None
    actor_email: str | None
    created_at: datetime


async def list_recent_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    limit: int = 10,
) -> list[RecentAuditActivity]:
    normalized_limit = max(1, min(limit, 50))

    result = await db.execute(
        text(
            """
            select
                al.id,
                al.action,
                al.resource,
                al.resource_id,
                al.status_code,
                al.message,
                al.actor_user_id,
                u.full_name as actor_full_name,
                u.email as actor_email,
                al.created_at
            from public.audit_logs al
            left join public.users u
              on u.id = al.actor_user_id
            where al.tenant_id = cast(:tenant_id as varchar)
            order by al.created_at desc, al.id desc
            limit :limit
            """
        ),
        {
            "tenant_id": tenant_id,
            "limit": normalized_limit,
        },
    )

    return [
        RecentAuditActivity(
            id=str(row["id"]),
            action=str(row["action"]),
            resource=str(row["resource"]) if row["resource"] else None,
            resource_id=str(row["resource_id"]) if row["resource_id"] else None,
            status_code=int(row["status_code"]) if row["status_code"] is not None else None,
            message=str(row["message"]) if row["message"] else None,
            actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] else None,
            actor_full_name=str(row["actor_full_name"]) if row["actor_full_name"] else None,
            actor_email=str(row["actor_email"]) if row["actor_email"] else None,
            created_at=row["created_at"],
        )
        for row in result.mappings().all()
    ]

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    tenant_id: UUID,
    event_type: str,
    request_id: Optional[str] = None,
    actor_user_id: Optional[UUID] = None,
    actor_ip: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    action: Optional[str] = None,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    changes: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Append-only audit write.

    Important:
    - Must never update existing rows (immutability).
    - Keep metadata minimal; avoid secrets and sensitive values.
    """
    row = AuditLog(
        tenant_id=tenant_id,
        request_id=request_id,
        actor_user_id=actor_user_id,
        actor_ip=actor_ip,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        message=message,
        metadata=metadata,
        changes=changes,
    )
    db.add(row)
    # Flush (not commit) so callers can control transaction boundaries.
    db.flush()
    return row

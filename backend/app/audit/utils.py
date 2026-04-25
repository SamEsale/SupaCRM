from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.audit.service import write_audit_log


def audit_event(
    request: Request,
    db: Session,
    *,
    tenant_id: UUID,
    event_type: str,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    changes: Optional[Dict[str, Any]] = None,
):
    """
    Convenience wrapper that uses request.state context.
    """
    return write_audit_log(
        db,
        tenant_id=tenant_id,
        event_type=event_type,
        request_id=getattr(request.state, "request_id", None),
        actor_user_id=getattr(request.state, "actor_user_id", None),
        actor_ip=getattr(request.state, "actor_ip", None),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        message=message,
        metadata=metadata,
        changes=changes,
    )

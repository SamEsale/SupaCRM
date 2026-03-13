from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogOut(BaseModel):
    id: UUID
    tenant_id: UUID
    request_id: Optional[str] = None
    actor_user_id: Optional[UUID] = None
    actor_ip: Optional[str] = None

    event_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    action: Optional[str] = None

    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    changes: Optional[Dict[str, Any]] = None

    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    # Minimal query model for admin use
    event_type: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    actor_user_id: Optional[UUID] = None
    request_id: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped

from app.db import Base, TenantMixin, TimestampMixin


class AuditLog(Base, TenantMixin, TimestampMixin):
    """
    Audit log for security and compliance.

    IMPORTANT:
    - Do NOT name an ORM attribute `metadata` (reserved by SQLAlchemy).
    - If you want the column name to be `metadata`, map it using Column("metadata", ...).
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Who did it
    actor_user_id = Column(String(36), nullable=True, index=True)
    actor_ip = Column(String(64), nullable=True)

    # Request correlation
    request_id = Column(String(64), nullable=True, index=True)

    # What happened
    action = Column(String(128), nullable=False, index=True)        # e.g. "auth.login", "crm.contact.create"
    resource = Column(String(128), nullable=True, index=True)       # e.g. "contact", "invoice"
    resource_id = Column(String(64), nullable=True, index=True)     # id of the entity impacted

    status_code = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)

    # Extra data (JSON)
    # Column name is "metadata" in DB, but attribute is "meta" in Python (SQLAlchemy-safe)
    meta = Column("metadata", JSONB, nullable=True)

    # TimestampMixin already adds created_at/updated_at

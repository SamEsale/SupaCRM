from sqlalchemy import Column, String, Boolean, DateTime, func
from app.db import Base


class Tenant(Base):
    __tablename__ = "tenants"

    # Use String(64) to align with tenant header usage and RLS GUC patterns.
    id = Column(String(64), primary_key=True)

    name = Column(String(255), nullable=False)

    # Legacy boolean retained for backward compatibility with current auth flow.
    is_active = Column(Boolean, nullable=False, server_default="true")

    # Explicit lifecycle status for Phase 2.5
    status = Column(String(32), nullable=False, server_default="active")
    status_reason = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
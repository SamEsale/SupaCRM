from sqlalchemy import Column, String, Boolean, DateTime, func
from app.db import Base


class Tenant(Base):
    __tablename__ = "tenants"

    # Use String(64) to align with your tenant_id header usage and RLS GUC patterns.
    id = Column(String(64), primary_key=True)

    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

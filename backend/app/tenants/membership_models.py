from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from app.db import Base


class TenantUser(Base):
    __tablename__ = "tenant_users"

    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    is_owner = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_users_tenant_user"),
    )

from __future__ import annotations

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text, func

from app.db import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    number = Column(String(50), nullable=False, unique=True, index=True)

    company_id = Column(
        String(36),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contact_id = Column(
        String(36),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
    )

    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)

    currency = Column(String(3), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)

    status = Column(String(32), nullable=False, default="draft")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


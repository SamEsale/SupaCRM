# Sales models
from __future__ import annotations

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text, func

from app.db import Base


class Deal(Base):
    __tablename__ = "deals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)

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
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
    )

    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)

    stage = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)

    expected_close_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True)
    follow_up_note = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

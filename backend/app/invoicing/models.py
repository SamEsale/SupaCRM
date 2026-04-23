from __future__ import annotations

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func

from app.db import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_invoices_tenant_number"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    number = Column(String(50), nullable=False, index=True)

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
    source_quote_id = Column(
        String(36),
        ForeignKey("quotes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
    )
    subscription_id = Column(
        String(36),
        ForeignKey("commercial_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    billing_cycle_id = Column(
        String(36),
        ForeignKey("commercial_billing_cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)

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

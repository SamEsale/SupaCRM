from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text, func

from app.db import Base


class InvoicePaymentRecord(Base):
    __tablename__ = "invoice_payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id = Column(
        String(36),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    method = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="completed", server_default="completed")
    payment_date = Column(DateTime(timezone=True), nullable=False)
    external_reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

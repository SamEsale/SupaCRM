from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func

from app.db import Base


class AccountingAccount(Base):
    __tablename__ = "accounting_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(32), nullable=False)
    name = Column(String(255), nullable=False)
    account_type = Column(String(32), nullable=False)
    system_key = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date = Column(Date, nullable=False)
    memo = Column(Text, nullable=False)
    source_type = Column(String(32), nullable=True)
    source_id = Column(String(64), nullable=True)
    source_event = Column(String(64), nullable=True)
    currency = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    journal_entry_id = Column(
        String(36),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id = Column(
        String(36),
        ForeignKey("accounting_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    line_order = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    debit_amount = Column(Numeric(12, 2), nullable=False, default=0)
    credit_amount = Column(Numeric(12, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

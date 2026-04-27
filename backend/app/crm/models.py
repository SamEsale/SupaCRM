from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, func

from app.db import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)

    email = Column(String(320), nullable=True)
    phone = Column(String(50), nullable=True)

    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_contacts_tenant_email"),
    )


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    website = Column(String(255), nullable=True)
    email = Column(String(320), nullable=True)
    phone = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True)

    address = Column(Text, nullable=True)
    vat_number = Column(String(64), nullable=True)
    registration_number = Column(String(64), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_companies_tenant_name"),
    )
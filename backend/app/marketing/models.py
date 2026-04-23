from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    channel = Column(String(32), nullable=False)
    audience_type = Column(String(32), nullable=False, server_default="all_contacts")
    audience_description = Column(Text, nullable=True)
    target_company_id = Column(
        String(36),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_contact_id = Column(
        String(36),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    subject = Column(String(255), nullable=True)
    message_body = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    blocked_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MarketingCampaignExecution(Base):
    __tablename__ = "marketing_campaign_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id = Column(
        String(36),
        ForeignKey("marketing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, server_default="blocked")
    initiated_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    total_recipients = Column(Integer, nullable=False, server_default="0")
    processed_recipients = Column(Integer, nullable=False, server_default="0")
    sent_recipients = Column(Integer, nullable=False, server_default="0")
    failed_recipients = Column(Integer, nullable=False, server_default="0")
    batch_size = Column(Integer, nullable=False, server_default="100")
    queued_batch_count = Column(Integer, nullable=False, server_default="0")
    queue_job_id = Column(String(64), nullable=True, index=True)
    blocked_reason = Column(Text, nullable=True)
    meta = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MarketingCampaignExecutionRecipient(Base):
    __tablename__ = "marketing_campaign_execution_recipients"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "email",
            name="uq_marketing_campaign_execution_recipients_execution_email",
        ),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id = Column(
        String(36),
        ForeignKey("marketing_campaign_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id = Column(
        String(36),
        ForeignKey("marketing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    support_ticket_id = Column(String(36), ForeignKey("support_tickets.id", ondelete="SET NULL"), nullable=True)
    email = Column(String(320), nullable=False)
    phone = Column(String(50), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company = Column(String(255), nullable=True)
    batch_number = Column(Integer, nullable=False, server_default="1")
    status = Column(String(32), nullable=False, server_default="pending")
    failure_reason = Column(Text, nullable=True)
    handoff_at = Column(DateTime(timezone=True), nullable=True)
    handoff_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    handoff_status = Column(String(32), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

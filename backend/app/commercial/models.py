from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class CommercialPlan(Base):
    __tablename__ = "commercial_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    provider = Column(String(32), nullable=False, server_default="stripe")
    provider_price_id = Column(String(128), nullable=True)
    billing_interval = Column(String(16), nullable=False)
    price_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    trial_days = Column(Integer, nullable=False, server_default="14")
    grace_days = Column(Integer, nullable=False, server_default="7")
    is_active = Column(Boolean, nullable=False, server_default="true")
    features = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CommercialSubscription(Base):
    __tablename__ = "commercial_subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    plan_id = Column(
        String(36),
        ForeignKey("commercial_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider = Column(String(32), nullable=False, server_default="stripe")
    provider_customer_id = Column(String(128), nullable=True, index=True)
    provider_subscription_id = Column(String(128), nullable=True, unique=True, index=True)
    subscription_status = Column(String(32), nullable=True)
    commercial_state = Column(String(32), nullable=False, server_default="trial")
    state_reason = Column(String(255), nullable=True)
    trial_start_at = Column(DateTime(timezone=True), nullable=True)
    trial_end_at = Column(DateTime(timezone=True), nullable=True)
    current_period_start_at = Column(DateTime(timezone=True), nullable=True)
    current_period_end_at = Column(DateTime(timezone=True), nullable=True)
    grace_end_at = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, server_default="false")
    activated_at = Column(DateTime(timezone=True), nullable=True)
    reactivated_at = Column(DateTime(timezone=True), nullable=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    meta = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CommercialBillingCycle(Base):
    __tablename__ = "commercial_billing_cycles"
    __table_args__ = (
        UniqueConstraint("subscription_id", "cycle_number", name="uq_commercial_billing_cycles_subscription_cycle"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id = Column(
        String(36),
        ForeignKey("commercial_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cycle_number = Column(Integer, nullable=False)
    period_start_at = Column(DateTime(timezone=True), nullable=False)
    period_end_at = Column(DateTime(timezone=True), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(32), nullable=False, server_default="pending")
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_event_id = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CommercialBillingEvent(Base):
    __tablename__ = "commercial_billing_events"
    __table_args__ = (
        UniqueConstraint("provider", "external_event_id", name="uq_commercial_billing_events_provider_external_event"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    subscription_id = Column(
        String(36),
        ForeignKey("commercial_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider = Column(String(32), nullable=False)
    external_event_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(128), nullable=False, index=True)
    processing_status = Column(String(32), nullable=False, server_default="received")
    action_taken = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CommercialPaymentMethod(Base):
    __tablename__ = "commercial_payment_methods"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(64),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_customer_id = Column(String(128), nullable=False, index=True)
    provider_payment_method_id = Column(String(128), nullable=False, unique=True, index=True)
    provider_type = Column(String(32), nullable=False, server_default="stripe")
    card_brand = Column(String(32), nullable=True)
    card_last4 = Column(String(4), nullable=True)
    card_exp_month = Column(Integer, nullable=True)
    card_exp_year = Column(Integer, nullable=True)
    billing_email = Column(String(255), nullable=True)
    billing_name = Column(String(255), nullable=True)
    is_default = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
    meta = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

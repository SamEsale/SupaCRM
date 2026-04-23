from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


CommercialState = Literal["pending", "trial", "active", "past_due", "grace", "suspended", "canceled"]
BillingCycleStatus = Literal["pending", "issued", "paid", "past_due", "grace", "suspended", "canceled", "void"]
BillingEventStatus = Literal["received", "processing", "processed", "failed"]


class CommercialPlanCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    provider: str = Field(default="stripe", min_length=1, max_length=32)
    provider_price_id: str | None = Field(default=None, max_length=128)
    billing_interval: str = Field(..., min_length=1, max_length=16)
    price_amount: Decimal = Field(..., ge=0, decimal_places=2, max_digits=12)
    currency: str = Field(..., min_length=3, max_length=3)
    trial_days: int = Field(default=14, ge=0, le=365)
    grace_days: int = Field(default=7, ge=0, le=365)
    is_active: bool = True
    features: dict[str, object] = Field(default_factory=dict)


class CommercialPlanUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    provider: str | None = Field(default=None, min_length=1, max_length=32)
    provider_price_id: str | None = Field(default=None, max_length=128)
    billing_interval: str | None = Field(default=None, min_length=1, max_length=16)
    price_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    trial_days: int | None = Field(default=None, ge=0, le=365)
    grace_days: int | None = Field(default=None, ge=0, le=365)
    is_active: bool | None = None
    features: dict[str, object] | None = None


class CommercialSubscriptionCreateRequest(BaseModel):
    plan_code: str = Field(..., min_length=1, max_length=64)
    provider: str = Field(default="stripe", min_length=1, max_length=32)
    start_trial: bool = True
    customer_email: str | None = Field(default=None, max_length=255)
    customer_name: str | None = Field(default=None, max_length=255)


class CommercialSubscriptionStateUpdateRequest(BaseModel):
    state: CommercialState
    reason: str | None = Field(default=None, max_length=255)


class CommercialPlanOut(BaseModel):
    id: str
    code: str
    plan_code: str
    name: str
    description: str | None = None
    provider: str
    provider_price_id: str | None = None
    billing_interval: str
    price_amount: Decimal
    currency: str
    trial_days: int
    grace_days: int
    is_active: bool
    features: dict[str, object]
    features_summary: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CommercialSubscriptionOut(BaseModel):
    id: str
    tenant_id: str
    plan_id: str
    plan_code: str
    plan_name: str
    provider: str
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    subscription_status: str | None = None
    commercial_state: CommercialState
    state_reason: str | None = None
    trial_start_at: datetime | None = None
    trial_end_at: datetime | None = None
    current_period_start_at: datetime | None = None
    current_period_end_at: datetime | None = None
    grace_end_at: datetime | None = None
    cancel_at_period_end: bool
    activated_at: datetime | None = None
    reactivated_at: datetime | None = None
    suspended_at: datetime | None = None
    canceled_at: datetime | None = None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CommercialBillingCycleOut(BaseModel):
    id: str
    tenant_id: str
    subscription_id: str
    cycle_number: int
    period_start_at: datetime
    period_end_at: datetime
    due_at: datetime
    amount: Decimal
    currency: str
    status: BillingCycleStatus
    invoice_id: str | None = None
    provider_event_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CommercialBillingEventOut(BaseModel):
    id: str
    tenant_id: str | None = None
    subscription_id: str | None = None
    provider: str
    external_event_id: str
    event_type: str
    processing_status: BillingEventStatus
    action_taken: str | None = None
    error_message: str | None = None
    raw_payload: dict[str, object]
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CommercialBillingCycleSummaryOut(BaseModel):
    id: str
    cycle_number: int
    period_start_at: datetime
    period_end_at: datetime
    due_at: datetime
    amount: Decimal
    currency: str
    status: BillingCycleStatus
    invoice_id: str | None = None
    created_at: datetime


class CommercialBillingEventSummaryOut(BaseModel):
    id: str
    provider: str
    external_event_id: str
    event_type: str
    processing_status: BillingEventStatus
    action_taken: str | None = None
    error_message: str | None = None
    processed_at: datetime | None = None
    created_at: datetime


class CommercialSubscriptionSummaryOut(BaseModel):
    subscription: CommercialSubscriptionOut | None = None
    recent_billing_cycles: list[CommercialBillingCycleSummaryOut] = Field(default_factory=list)
    recent_billing_events: list[CommercialBillingEventSummaryOut] = Field(default_factory=list)


class TenantCommercialStatusOut(BaseModel):
    current_plan: CommercialPlanOut | None = None
    subscription: CommercialSubscriptionOut | None = None
    subscription_status: str | None = None
    trial_status: Literal["active", "ended", "not_applicable"]
    next_billing_at: datetime | None = None
    renewal_at: datetime | None = None
    provider: str | None = None
    provider_name: str | None = None
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    commercially_active: bool


class CommercialLifecycleResponse(BaseModel):
    plan: CommercialPlanOut | None = None
    subscription: CommercialSubscriptionOut | None = None
    billing_cycle: CommercialBillingCycleOut | None = None
    billing_event: CommercialBillingEventOut | None = None


class CommercialPaymentMethodOut(BaseModel):
    id: str
    tenant_id: str
    provider_customer_id: str
    provider_payment_method_id: str
    provider_type: str
    card_brand: str | None = None
    card_last4: str | None = None
    card_exp_month: int | None = None
    card_exp_year: int | None = None
    billing_email: str | None = None
    billing_name: str | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CommercialPaymentMethodCreateRequest(BaseModel):
    provider_payment_method_id: str = Field(..., max_length=128)
    billing_email: str | None = Field(default=None, max_length=255)
    billing_name: str | None = Field(default=None, max_length=255)


class CommercialPaymentMethodUpdateRequest(BaseModel):
    is_default: bool | None = None
    is_active: bool | None = None
    billing_email: str | None = Field(default=None, max_length=255)
    billing_name: str | None = Field(default=None, max_length=255)


class CommercialPaymentMethodListResponse(BaseModel):
    items: list[CommercialPaymentMethodOut]
    total: int


class CommercialCheckoutSessionRequest(BaseModel):
    customer_email: str | None = Field(default=None, max_length=255)
    customer_name: str | None = Field(default=None, max_length=255)


class CommercialCheckoutSessionOut(BaseModel):
    provider: str
    session_id: str
    url: str
    mode: Literal["setup", "subscription"]
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None


class CommercialSubscriptionChangePlanRequest(BaseModel):
    new_plan_code: str = Field(..., min_length=1, max_length=64)
    prorate: bool = True


class CommercialTrialConversionRequest(BaseModel):
    payment_method_id: str | None = Field(default=None, max_length=36)
    plan_code: str | None = Field(default=None, min_length=1, max_length=64)

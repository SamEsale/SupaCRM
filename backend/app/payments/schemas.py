from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


PaymentMethod = Literal[
    "bank_transfer",
    "cash",
    "card_manual",
    "other",
]

PaymentStatus = Literal[
    "pending",
    "completed",
    "failed",
    "cancelled",
]

InvoicePaymentState = Literal[
    "unpaid",
    "partially paid",
    "paid",
]

PaymentGatewayProvider = Literal[
    "stripe",
    "revolut_business",
    "payoneer",
]

PaymentGatewayMode = Literal[
    "test",
    "live",
]

PaymentGatewayConfigurationState = Literal[
    "not_configured",
    "incomplete",
    "configured",
]

PaymentProviderFoundationState = Literal[
    "disabled",
    "needs_configuration",
    "manual_only",
    "ready",
]


class InvoicePaymentCreateRequest(BaseModel):
    invoice_id: str = Field(..., min_length=1, max_length=36)
    amount: Decimal = Field(..., gt=0, decimal_places=2, max_digits=12)
    currency: str = Field(..., min_length=3, max_length=3)
    method: PaymentMethod
    status: PaymentStatus = "completed"
    payment_date: datetime
    external_reference: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class InvoicePaymentOut(BaseModel):
    id: str
    tenant_id: str
    invoice_id: str
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    payment_date: datetime
    external_reference: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class InvoicePaymentListResponse(BaseModel):
    items: list[InvoicePaymentOut]
    total: int


class InvoicePaymentSummaryOut(BaseModel):
    invoice_id: str
    currency: str
    invoice_total_amount: Decimal
    completed_amount: Decimal
    pending_amount: Decimal
    outstanding_amount: Decimal
    payment_count: int
    completed_payment_count: int
    pending_payment_count: int
    payment_state: InvoicePaymentState


class PaymentGatewayProviderSettingsOut(BaseModel):
    provider: PaymentGatewayProvider
    display_name: str
    is_enabled: bool
    is_default: bool
    mode: PaymentGatewayMode
    account_id: str | None = None
    merchant_id: str | None = None
    publishable_key: str | None = None
    client_id: str | None = None
    secret_key_set: bool
    api_key_set: bool
    client_secret_set: bool
    webhook_secret_set: bool
    configuration_state: PaymentGatewayConfigurationState
    validation_errors: list[str]
    updated_at: datetime | None = None


class PaymentGatewaySettingsSnapshotOut(BaseModel):
    default_provider: PaymentGatewayProvider | None = None
    providers: list[PaymentGatewayProviderSettingsOut]
    updated_at: datetime | None = None


class PaymentProviderFoundationOut(BaseModel):
    provider: PaymentGatewayProvider
    display_name: str
    is_enabled: bool
    is_default: bool
    mode: PaymentGatewayMode
    configuration_state: PaymentGatewayConfigurationState
    foundation_state: PaymentProviderFoundationState
    supports_checkout_payments: bool
    supports_webhooks: bool
    supports_automated_subscriptions: bool
    operator_summary: str
    validation_errors: list[str]
    updated_at: datetime | None = None


class PaymentProviderFoundationSnapshotOut(BaseModel):
    default_provider: PaymentGatewayProvider | None = None
    providers: list[PaymentProviderFoundationOut]
    updated_at: datetime | None = None


class PaymentGatewayProviderUpdateRequest(BaseModel):
    is_enabled: bool = False
    is_default: bool = False
    mode: PaymentGatewayMode = "test"
    account_id: str | None = Field(default=None, max_length=255)
    merchant_id: str | None = Field(default=None, max_length=255)
    publishable_key: str | None = Field(default=None, max_length=255)
    client_id: str | None = Field(default=None, max_length=255)
    secret_key: str | None = Field(default=None, max_length=255)
    api_key: str | None = Field(default=None, max_length=255)
    client_secret: str | None = Field(default=None, max_length=255)
    webhook_secret: str | None = Field(default=None, max_length=255)

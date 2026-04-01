from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


InvoiceStatus = Literal[
    "draft",
    "issued",
    "paid",
    "overdue",
    "cancelled",
]


class InvoiceCreateRequest(BaseModel):
    company_id: str = Field(..., min_length=1, max_length=36)
    contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    product_id: str | None = Field(default=None, min_length=1, max_length=36)
    issue_date: date
    due_date: date
    currency: str = Field(..., min_length=3, max_length=3)
    total_amount: Decimal = Field(..., ge=0, decimal_places=2, max_digits=12)
    notes: str | None = None


class InvoiceUpdateRequest(BaseModel):
    company_id: str | None = Field(default=None, min_length=1, max_length=36)
    contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    product_id: str | None = Field(default=None, min_length=1, max_length=36)
    issue_date: date | None = None
    due_date: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    total_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    status: InvoiceStatus | None = None
    notes: str | None = None


class InvoiceStatusUpdateRequest(BaseModel):
    status: InvoiceStatus


class InvoiceOut(BaseModel):
    id: str
    tenant_id: str
    number: str
    company_id: str
    contact_id: str | None = None
    product_id: str | None = None
    issue_date: date
    due_date: date
    currency: str
    total_amount: Decimal
    status: InvoiceStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    items: list[InvoiceOut]
    total: int

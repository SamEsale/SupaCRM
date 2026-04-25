from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


ExpenseStatus = Literal[
    "draft",
    "submitted",
    "approved",
    "paid",
]


class ExpenseCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    amount: Decimal = Field(..., gt=0, decimal_places=2, max_digits=12)
    currency: str = Field(..., min_length=3, max_length=3)
    expense_date: date
    category: str = Field(..., min_length=1, max_length=64)
    status: ExpenseStatus = "draft"
    vendor_name: str | None = Field(default=None, max_length=255)


class ExpenseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    amount: Decimal | None = Field(default=None, gt=0, decimal_places=2, max_digits=12)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    expense_date: date | None = None
    category: str | None = Field(default=None, min_length=1, max_length=64)
    status: ExpenseStatus | None = None
    vendor_name: str | None = Field(default=None, max_length=255)


class ExpenseOut(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str | None = None
    amount: Decimal
    currency: str
    expense_date: date
    category: str
    status: ExpenseStatus
    vendor_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    items: list[ExpenseOut]
    total: int

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


DealStage = Literal[
    "new lead",
    "qualified lead",
    "proposal sent",
    "estimate sent",
    "negotiating contract terms",
    "contract signed",
    "deal not secured",
]

DealStatus = Literal[
    "open",
    "in progress",
    "won",
    "lost",
]


class DealCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    company_id: str = Field(..., min_length=1, max_length=36)
    contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    product_id: str | None = Field(default=None, min_length=1, max_length=36)
    amount: Decimal = Field(..., ge=0, decimal_places=2, max_digits=12)
    currency: str = Field(..., min_length=3, max_length=3)
    stage: DealStage
    status: DealStatus
    expected_close_date: date | None = None
    notes: str | None = None


class DealUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    company_id: str | None = Field(default=None, min_length=1, max_length=36)
    contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    product_id: str | None = Field(default=None, min_length=1, max_length=36)
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    stage: DealStage | None = None
    status: DealStatus | None = None
    expected_close_date: date | None = None
    notes: str | None = None


class DealOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    company_id: str
    contact_id: str | None = None
    product_id: str | None = None
    amount: Decimal
    currency: str
    stage: DealStage
    status: DealStatus
    expected_close_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class DealListResponse(BaseModel):
    items: list[DealOut]
    total: int


class PipelineStageCountOut(BaseModel):
    stage: DealStage
    count: int


class PipelineReportResponse(BaseModel):
    items: list[PipelineStageCountOut]
    total: int


class DeleteResponse(BaseModel):
    success: bool
    message: str

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


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

DealListView = Literal[
    "all",
    "opportunities",
]


LeadSource = Literal[
    "manual",
    "website",
    "email",
    "phone",
    "referral",
    "whatsapp",
    "other",
]

LeadImportStage = Literal[
    "new lead",
    "qualified lead",
]

LeadImportStatus = Literal[
    "open",
    "in progress",
]

LeadImportRowStatus = Literal["imported", "error"]


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


class DealFollowUpUpdateRequest(BaseModel):
    next_follow_up_at: datetime | None = None
    follow_up_note: str | None = None


class LeadCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    company_id: str = Field(..., min_length=1, max_length=36)
    contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    amount: Decimal = Field(..., ge=0, decimal_places=2, max_digits=12)
    currency: str = Field(..., min_length=3, max_length=3)
    source: LeadSource | None = None
    notes: str | None = None


class LeadImportRequest(BaseModel):
    csv_text: str = Field(..., min_length=1)
    create_missing_companies: bool = False


class LeadImportRowOut(BaseModel):
    row_number: int
    name: str | None = None
    company: str | None = None
    email: str | None = None
    stage: str | None = None
    status: str | None = None
    result: LeadImportRowStatus
    message: str


class LeadImportResultOut(BaseModel):
    total_rows: int
    imported_rows: int
    error_rows: int
    rows: list[LeadImportRowOut]


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
    next_follow_up_at: datetime | None = None
    follow_up_note: str | None = None
    closed_at: datetime | None = None
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


class SalesStageSummaryOut(BaseModel):
    stage: DealStage
    count: int
    open_amount: Decimal
    weighted_amount: Decimal


class SalesForecastSummaryOut(BaseModel):
    total_open_pipeline_amount: Decimal
    weighted_pipeline_amount: Decimal
    won_amount: Decimal
    lost_amount: Decimal
    deals_won_this_period_count: int
    deals_won_this_period_amount: Decimal
    deals_lost_this_period_count: int
    deals_lost_this_period_amount: Decimal
    overdue_follow_up_count: int
    due_today_follow_up_count: int
    upcoming_follow_up_count: int
    currencies: list[str]
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


class SalesForecastReportResponse(BaseModel):
    summary: SalesForecastSummaryOut
    stage_breakdown: list[SalesStageSummaryOut]
    opportunity_stage_breakdown: list[SalesStageSummaryOut]


class DeleteResponse(BaseModel):
    success: bool
    message: str

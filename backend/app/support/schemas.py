from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SupportTicketStatus = Literal[
    "open",
    "in progress",
    "waiting on customer",
    "resolved",
    "closed",
]

SupportTicketPriority = Literal[
    "low",
    "medium",
    "high",
    "urgent",
]

SupportTicketSource = Literal[
    "manual",
    "email",
    "whatsapp",
    "phone",
    "web",
]


class SupportTicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    status: SupportTicketStatus = "open"
    priority: SupportTicketPriority = "medium"
    source: SupportTicketSource = "manual"
    company_id: str | None = Field(default=None, min_length=1, max_length=36)
    contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    assigned_to_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    related_deal_id: str | None = Field(default=None, min_length=1, max_length=36)
    related_invoice_id: str | None = Field(default=None, min_length=1, max_length=36)


class SupportTicketUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    status: SupportTicketStatus | None = None
    priority: SupportTicketPriority | None = None
    source: SupportTicketSource | None = None
    company_id: str | None = Field(default=None, min_length=1, max_length=36)
    contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    assigned_to_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    related_deal_id: str | None = Field(default=None, min_length=1, max_length=36)
    related_invoice_id: str | None = Field(default=None, min_length=1, max_length=36)


class SupportTicketOut(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str
    status: SupportTicketStatus
    priority: SupportTicketPriority
    source: SupportTicketSource
    company_id: str | None = None
    company_name: str | None = None
    contact_id: str | None = None
    contact_name: str | None = None
    assigned_to_user_id: str | None = None
    assigned_to_full_name: str | None = None
    assigned_to_email: str | None = None
    related_deal_id: str | None = None
    related_deal_name: str | None = None
    related_invoice_id: str | None = None
    related_invoice_number: str | None = None
    created_at: datetime
    updated_at: datetime


class SupportTicketListResponse(BaseModel):
    items: list[SupportTicketOut]
    total: int


class SupportSummaryOut(BaseModel):
    open_count: int
    in_progress_count: int
    urgent_count: int
    resolved_this_period_count: int
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime

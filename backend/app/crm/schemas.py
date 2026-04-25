from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class ContactCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company_id: str | None = Field(default=None, max_length=36)
    company: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ContactUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company_id: str | None = Field(default=None, max_length=36)
    company: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ContactOut(BaseModel):
    id: str
    tenant_id: str
    first_name: str
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company_id: str | None = None
    company: str | None = None
    job_title: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ContactListResponse(BaseModel):
    items: list[ContactOut]
    total: int


class ContactListQuery(BaseModel):
    q: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


ContactImportRowStatus = Literal["imported", "error"]


class ContactImportRequest(BaseModel):
    csv_text: str = Field(..., min_length=1)
    create_missing_companies: bool = False


class ContactImportRowOut(BaseModel):
    row_number: int
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    company: str | None = None
    status: ContactImportRowStatus
    message: str


class ContactImportResultOut(BaseModel):
    total_rows: int
    imported_rows: int
    error_rows: int
    rows: list[ContactImportRowOut]


class CompanyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    industry: str | None = Field(default=None, max_length=100)
    address: str | None = None
    vat_number: str | None = Field(default=None, max_length=64)
    registration_number: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    industry: str | None = Field(default=None, max_length=100)
    address: str | None = None
    vat_number: str | None = Field(default=None, max_length=64)
    registration_number: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class CompanyOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    industry: str | None = None
    address: str | None = None
    vat_number: str | None = None
    registration_number: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    items: list[CompanyOut]
    total: int


class CompanyListQuery(BaseModel):
    q: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class DeleteResponse(BaseModel):
    success: bool
    message: str

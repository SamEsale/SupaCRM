from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


TenantStatus = Literal["active", "suspended", "disabled"]


class TenantOut(BaseModel):
    id: str
    name: str
    is_active: bool
    status: TenantStatus
    status_reason: str | None = None
    legal_name: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_region: str | None = None
    postal_code: str | None = None
    country: str | None = None
    vat_number: str | None = None
    default_currency: str
    secondary_currency: str | None = None
    secondary_currency_rate: Decimal | None = None
    secondary_currency_rate_source: str | None = None
    secondary_currency_rate_as_of: datetime | None = None
    brand_primary_color: str | None = None
    brand_secondary_color: str | None = None
    sidebar_background_color: str | None = None
    sidebar_text_color: str | None = None
    logo_file_key: str | None = None
    created_at: datetime
    updated_at: datetime


class TenantBrandingOut(BaseModel):
    tenant_id: str
    logo_file_key: str | None = None
    logo_url: str | None = None
    brand_primary_color: str = "#2563EB"
    brand_secondary_color: str = "#1D4ED8"
    sidebar_background_color: str = "#111827"
    sidebar_text_color: str = "#FFFFFF"


class TenantBrandingUpdateRequest(BaseModel):
    logo_file_key: str | None = Field(default=None, max_length=2048)


class TenantUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state_region: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=40)
    country: str | None = Field(default=None, max_length=120)
    vat_number: str | None = Field(default=None, max_length=64)
    default_currency: str = Field(..., min_length=3, max_length=3)
    secondary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    secondary_currency_rate: Decimal | None = Field(default=None)
    brand_primary_color: str | None = Field(default=None, max_length=7)
    brand_secondary_color: str | None = Field(default=None, max_length=7)
    sidebar_background_color: str | None = Field(default=None, max_length=7)
    sidebar_text_color: str | None = Field(default=None, max_length=7)


class TenantStatusUpdateRequest(BaseModel):
    status: TenantStatus
    status_reason: str | None = Field(default=None, max_length=255)


class TenantRoleOut(BaseModel):
    id: str
    name: str
    permission_codes: list[str]
    created_at: datetime


class TenantUserOut(BaseModel):
    user_id: str
    email: str
    full_name: str | None = None
    user_is_active: bool
    membership_is_active: bool
    is_owner: bool
    role_names: list[str]
    membership_created_at: datetime


class TenantUserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = None
    role_names: list[str] = Field(default_factory=lambda: ["user"])
    is_owner: bool = False


class TenantRoleAssignmentRequest(BaseModel):
    role_names: list[str] = Field(..., min_length=1)
    is_owner: bool = False


class RoleAssignmentOut(BaseModel):
    role_name: str
    role_id: str
    created_assignment: bool


class TenantUserProvisionOut(BaseModel):
    tenant_id: str
    user_id: str
    email: str
    created_user: bool
    created_credentials: bool
    password_set: bool
    created_membership: bool
    is_owner: bool
    assigned_roles: list[str]
    created_role_assignments: list[str]


class TenantRoleAssignmentBatchOut(BaseModel):
    tenant_id: str
    user_id: str
    is_owner: bool
    assigned_roles: list[str]
    created_role_assignments: list[str]

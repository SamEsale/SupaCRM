from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


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
    default_currency: str | None = None
    secondary_currency: str | None = None
    secondary_currency_rate: Decimal | None = None
    secondary_currency_rate_source: str | None = None
    secondary_currency_rate_as_of: datetime | None = None
    logo_file_key: str | None = None
    brand_primary_color: str | None = None
    brand_secondary_color: str | None = None
    sidebar_background_color: str | None = None
    sidebar_text_color: str | None = None
    created_at: datetime
    updated_at: datetime


class TenantBrandingOut(BaseModel):
    tenant_id: str
    logo_file_key: str | None = None
    logo_url: str | None = None
    brand_primary_color: str | None = None
    brand_secondary_color: str | None = None
    sidebar_background_color: str | None = None
    sidebar_text_color: str | None = None


class TenantBrandingUpdateRequest(BaseModel):
    logo_file_key: str | None = Field(default=None, max_length=512)


class TenantCommercialSubscriptionOut(BaseModel):
    id: str
    plan_code: str
    plan_name: str
    commercial_state: str
    plan_features: dict[str, object] = Field(default_factory=dict)
    trial_end_at: datetime | None = None
    current_period_end_at: datetime | None = None
    grace_end_at: datetime | None = None
    canceled_at: datetime | None = None


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
    default_currency: str = Field(default="USD", min_length=3, max_length=3)
    secondary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    secondary_currency_rate: Decimal | None = Field(default=None, gt=0)
    brand_primary_color: str | None = Field(default=None, min_length=7, max_length=7)
    brand_secondary_color: str | None = Field(default=None, min_length=7, max_length=7)
    sidebar_background_color: str | None = Field(default=None, min_length=7, max_length=7)
    sidebar_text_color: str | None = Field(default=None, min_length=7, max_length=7)

    @field_validator(
        "brand_primary_color",
        "brand_secondary_color",
        "sidebar_background_color",
        "sidebar_text_color",
    )
    @classmethod
    def validate_hex_color(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().upper()
        if not normalized:
            return None

        if len(normalized) != 7 or normalized[0] != "#" or any(character not in "0123456789ABCDEF" for character in normalized[1:]):
            raise ValueError("Brand colors must use the #RRGGBB hex format")

        return normalized


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


class TenantMembershipUpdateRequest(BaseModel):
    membership_is_active: bool | None = None
    is_owner: bool | None = None
    transfer_owner_from_user_id: str | None = Field(default=None, max_length=36)


class TenantMembershipOut(BaseModel):
    tenant_id: str
    user_id: str
    membership_is_active: bool
    is_owner: bool
    transferred_owner_from_user_id: str | None = None


class TenantMembershipRemovalOut(BaseModel):
    tenant_id: str
    user_id: str
    removed: bool


class TenantOnboardingOut(BaseModel):
    tenant: TenantOut
    commercial_subscription: TenantCommercialSubscriptionOut | None = None
    users_total: int
    owner_count: int
    admin_count: int
    bootstrap_complete: bool
    ready_for_use: bool
    missing_steps: list[str]
    warnings: list[str]
    next_action: str

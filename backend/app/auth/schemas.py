from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.commercial.schemas import TenantCommercialStatusOut


class LoginRequest(BaseModel):
    tenant_id: str | None = None
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    plan_code: str = Field(..., min_length=1, max_length=64)
    provider: str = Field(default="stripe", min_length=1, max_length=32)
    start_trial: bool = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    tenant_id: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
    revoke_family: bool = False


class PasswordResetRequest(BaseModel):
    tenant_id: str
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetResponse(BaseModel):
    message: str


class CurrentUserResponse(BaseModel):
    user_id: str
    tenant_id: str
    email: EmailStr
    full_name: str | None = None
    roles: list[str]
    is_owner: bool
    user_is_active: bool
    membership_is_active: bool
    tenant_is_active: bool


class LogoutResponse(BaseModel):
    success: bool = True


class MessageResponse(BaseModel):
    message: str = Field(..., min_length=1)


class RegisterResponse(TokenResponse):
    tenant_name: str
    commercial_status: TenantCommercialStatusOut

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
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

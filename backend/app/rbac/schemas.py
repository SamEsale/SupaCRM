from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PermissionOut(BaseModel):
    """Permission output schema."""
    id: str
    code: str
    description: str
    created_at: datetime


class PermissionCreateRequest(BaseModel):
    """Request to create a custom permission."""
    code: str = Field(..., min_length=3, max_length=64)
    description: str = Field(..., min_length=10, max_length=255)


class RoleCreateRequest(BaseModel):
    """Request to create a custom role."""
    name: str = Field(..., min_length=2, max_length=64)
    permission_ids: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    """Request to update a role."""
    name: str | None = Field(default=None, min_length=2, max_length=64)
    permission_ids: list[str] | None = None


class RoleOut(BaseModel):
    """Role output schema."""
    id: str
    tenant_id: str
    name: str
    permission_ids: list[str]
    created_at: datetime


class RoleWithPermissionsOut(BaseModel):
    """Role with full permission details."""
    id: str
    tenant_id: str
    name: str
    permissions: list[PermissionOut]
    created_at: datetime


class UserUpdateRequest(BaseModel):
    """Request to update a user's details."""
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class UserPasswordChangeRequest(BaseModel):
    """Request for user to change their password."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12, max_length=128)


class AdminPasswordSetRequest(BaseModel):
    """Request for admin to set a user's password."""
    password: str = Field(..., min_length=12, max_length=128)


class MembershipUpdateRequest(BaseModel):
    """Request to update membership status."""
    membership_is_active: bool | None = None
    is_owner: bool | None = None


class SessionOut(BaseModel):
    """Active session output."""
    id: str
    user_id: str
    tenant_id: str
    created_at: datetime
    last_used_at: datetime
    ip_address: str | None
    user_agent: str | None
    is_current: bool


class AuditLogOut(BaseModel):
    """Audit log entry output."""
    id: str
    tenant_id: str
    user_id: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogListOut(BaseModel):
    """Paginated audit log list."""
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int

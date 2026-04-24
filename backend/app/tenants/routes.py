from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.rbac.permissions import PERMISSION_TENANT_ADMIN
from app.tenants.schemas import (
    TenantOut,
    TenantRoleAssignmentBatchOut,
    TenantRoleAssignmentRequest,
    TenantRoleOut,
    TenantStatusUpdateRequest,
    TenantUpdateRequest,
    TenantUserCreateRequest,
    TenantUserOut,
    TenantUserProvisionOut,
)
from app.tenants.service import (
    assign_roles_to_tenant_user,
    get_tenant_details,
    list_tenant_roles,
    list_tenant_users,
    provision_tenant_user,
    update_tenant_details,
    update_tenant_status,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _raise_for_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if detail.startswith("Tenant does not exist"):
        status_code = status.HTTP_404_NOT_FOUND
    if detail.startswith("Roles not found"):
        status_code = status.HTTP_404_NOT_FOUND
    if detail.startswith("User is not a member"):
        status_code = status.HTTP_404_NOT_FOUND
    return HTTPException(status_code=status_code, detail=detail)


def _raise_for_tenant_update_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if detail.startswith("Tenant does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get(
    "/me",
    response_model=TenantOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def get_current_tenant(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> TenantOut:
    tenant = await get_tenant_details(db, tenant_id=tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantOut(**asdict(tenant))


@router.patch(
    "/me",
    response_model=TenantOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def update_current_tenant(
    payload: TenantUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> TenantOut:
    try:
        tenant = await update_tenant_details(
            db,
            tenant_id=tenant_id,
            name=payload.name.strip(),
            legal_name=payload.legal_name,
            address_line_1=payload.address_line_1,
            address_line_2=payload.address_line_2,
            city=payload.city,
            state_region=payload.state_region,
            postal_code=payload.postal_code,
            country=payload.country,
            vat_number=payload.vat_number,
            default_currency=payload.default_currency,
            secondary_currency=payload.secondary_currency,
            secondary_currency_rate=payload.secondary_currency_rate,
            brand_primary_color=payload.brand_primary_color,
            brand_secondary_color=payload.brand_secondary_color,
            sidebar_background_color=payload.sidebar_background_color,
            sidebar_text_color=payload.sidebar_text_color,
        )
    except ValueError as exc:
        raise _raise_for_tenant_update_error(exc) from exc
    return TenantOut(**asdict(tenant))


@router.patch(
    "/me/status",
    response_model=TenantOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def update_current_tenant_status(
    payload: TenantStatusUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> TenantOut:
    try:
        tenant = await update_tenant_status(
            db,
            tenant_id=tenant_id,
            status=payload.status,
            status_reason=payload.status_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TenantOut(**asdict(tenant))


@router.get(
    "/me/roles",
    response_model=list[TenantRoleOut],
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def get_current_tenant_roles(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> list[TenantRoleOut]:
    roles = await list_tenant_roles(db, tenant_id=tenant_id)
    return [TenantRoleOut(**asdict(role)) for role in roles]


@router.get(
    "/me/users",
    response_model=list[TenantUserOut],
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def get_current_tenant_users(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> list[TenantUserOut]:
    users = await list_tenant_users(db, tenant_id=tenant_id)
    return [TenantUserOut(**asdict(user)) for user in users]


@router.post(
    "/me/users",
    response_model=TenantUserProvisionOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def create_or_attach_tenant_user(
    payload: TenantUserCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> TenantUserProvisionOut:
    try:
        result = await provision_tenant_user(
            db,
            tenant_id=tenant_id,
            email=payload.email,
            full_name=payload.full_name,
            password=payload.password,
            role_names=payload.role_names,
            is_owner=payload.is_owner,
        )
    except ValueError as exc:
        raise _raise_for_service_error(exc) from exc

    return TenantUserProvisionOut(
        tenant_id=result.tenant_id,
        user_id=result.user.user_id,
        email=result.user.email,
        created_user=result.user.created_user,
        created_credentials=result.user.created_credentials,
        password_set=result.user.password_set,
        created_membership=result.membership.created_membership,
        is_owner=result.membership.is_owner,
        assigned_roles=[assignment.role_name for assignment in result.role_assignments],
        created_role_assignments=[
            assignment.role_name for assignment in result.role_assignments if assignment.created_assignment
        ],
    )


@router.post(
    "/me/users/{user_id}/roles",
    response_model=TenantRoleAssignmentBatchOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def assign_roles_for_tenant_user(
    user_id: str,
    payload: TenantRoleAssignmentRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> TenantRoleAssignmentBatchOut:
    try:
        result = await assign_roles_to_tenant_user(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            role_names=payload.role_names,
            is_owner=payload.is_owner,
        )
    except ValueError as exc:
        raise _raise_for_service_error(exc) from exc

    return TenantRoleAssignmentBatchOut(
        tenant_id=result.tenant_id,
        user_id=result.user_id,
        is_owner=result.is_owner,
        assigned_roles=[assignment.role_name for assignment in result.role_assignments],
        created_role_assignments=[
            assignment.role_name for assignment in result.role_assignments if assignment.created_assignment
        ],
    )

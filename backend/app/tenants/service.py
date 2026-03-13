from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import UserProvisionResult, provision_user
from app.db import reset_tenant_guc, set_tenant_guc
from app.rbac.service import RbacSeedResult, seed_default_rbac


@dataclass(slots=True)
class TenantProvisionResult:
    tenant_id: str
    tenant_name: str
    created_tenant: bool


@dataclass(slots=True)
class MembershipProvisionResult:
    tenant_id: str
    user_id: str
    created_membership: bool
    is_owner: bool


@dataclass(slots=True)
class RoleAssignmentResult:
    role_name: str
    role_id: str
    created_assignment: bool


@dataclass(slots=True)
class TenantUserProvisionResult:
    tenant_id: str
    user: UserProvisionResult
    membership: MembershipProvisionResult
    role_assignments: list[RoleAssignmentResult] = field(default_factory=list)


AdminProvisionResult = TenantUserProvisionResult


@dataclass(slots=True)
class TenantBootstrapResult:
    tenant: TenantProvisionResult
    rbac: RbacSeedResult
    admin: TenantUserProvisionResult


@dataclass(slots=True)
class TenantDetails:
    id: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class TenantRoleSummary:
    id: str
    name: str
    permission_codes: list[str]
    created_at: datetime


@dataclass(slots=True)
class TenantUserSummary:
    user_id: str
    email: str
    full_name: str | None
    user_is_active: bool
    membership_is_active: bool
    is_owner: bool
    role_names: list[str]
    membership_created_at: datetime


@dataclass(slots=True)
class TenantRoleAssignmentBatchResult:
    tenant_id: str
    user_id: str
    is_owner: bool
    role_assignments: list[RoleAssignmentResult] = field(default_factory=list)


async def bootstrap_tenant(
    session: AsyncSession,
    tenant_id: str,
    tenant_name: str,
    admin_email: str,
    admin_full_name: str | None,
    admin_password: str | None,
) -> TenantBootstrapResult:
    tenant = await ensure_tenant(
        session,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
    )

    await set_tenant_guc(session, tenant_id)
    try:
        rbac = await seed_default_rbac(session, tenant_id=tenant_id)
        admin = await provision_tenant_user(
            session,
            tenant_id=tenant_id,
            email=admin_email,
            full_name=admin_full_name,
            password=admin_password,
            role_names=("owner", "admin"),
            is_owner=True,
            role_ids_by_name=rbac.role_ids_by_name,
        )
    finally:
        await reset_tenant_guc(session)

    return TenantBootstrapResult(tenant=tenant, rbac=rbac, admin=admin)


async def ensure_tenant(
    session: AsyncSession,
    tenant_id: str,
    tenant_name: str,
) -> TenantProvisionResult:
    existing_tenant = await _tenant_exists(session, tenant_id=tenant_id)

    await session.execute(
        text(
            """
            insert into public.tenants (id, name, is_active)
            values (
                cast(:tenant_id as varchar),
                cast(:tenant_name as varchar),
                true
            )
            on conflict (id) do update
              set name = excluded.name,
                  is_active = true,
                  updated_at = now()
            """
        ),
        {"tenant_id": tenant_id, "tenant_name": tenant_name},
    )

    return TenantProvisionResult(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        created_tenant=not existing_tenant,
    )


async def get_tenant_details(session: AsyncSession, tenant_id: str) -> TenantDetails | None:
    result = await session.execute(
        text(
            """
            select id, name, is_active, created_at, updated_at
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        return None

    return TenantDetails(
        id=str(row["id"]),
        name=str(row["name"]),
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def update_tenant_details(
    session: AsyncSession,
    tenant_id: str,
    name: str,
) -> TenantDetails:
    result = await session.execute(
        text(
            """
            update public.tenants
            set name = cast(:name as varchar),
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            returning id, name, is_active, created_at, updated_at
            """
        ),
        {"tenant_id": tenant_id, "name": name},
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(f"Tenant does not exist: {tenant_id}")

    return TenantDetails(
        id=str(row["id"]),
        name=str(row["name"]),
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_tenant_roles(session: AsyncSession, tenant_id: str) -> list[TenantRoleSummary]:
    result = await session.execute(
        text(
            """
            select
                r.id,
                r.name,
                r.created_at,
                coalesce(
                    array_agg(distinct p.code) filter (where p.code is not null),
                    '{}'
                ) as permission_codes
            from public.roles r
            left join public.role_permissions rp
              on rp.role_id = r.id
            left join public.permissions p
              on p.id = rp.permission_id
            where r.tenant_id = cast(:tenant_id as varchar)
            group by r.id, r.name, r.created_at
            order by r.name
            """
        ),
        {"tenant_id": tenant_id},
    )

    roles: list[TenantRoleSummary] = []
    for row in result.mappings():
        roles.append(
            TenantRoleSummary(
                id=str(row["id"]),
                name=str(row["name"]),
                permission_codes=list(row["permission_codes"] or []),
                created_at=row["created_at"],
            )
        )
    return roles


async def list_tenant_users(session: AsyncSession, tenant_id: str) -> list[TenantUserSummary]:
    result = await session.execute(
        text(
            """
            select
                u.id as user_id,
                u.email,
                u.full_name,
                u.is_active as user_is_active,
                tu.is_active as membership_is_active,
                tu.is_owner,
                tu.created_at as membership_created_at,
                coalesce(
                    array_agg(distinct r.name) filter (where r.name is not null),
                    '{}'
                ) as role_names
            from public.tenant_users tu
            join public.users u
              on u.id = tu.user_id
            left join public.tenant_user_roles tur
              on tur.tenant_id = tu.tenant_id
             and tur.user_id = tu.user_id
            left join public.roles r
              on r.id = tur.role_id
             and r.tenant_id = tu.tenant_id
            where tu.tenant_id = cast(:tenant_id as varchar)
            group by
                u.id,
                u.email,
                u.full_name,
                u.is_active,
                tu.is_active,
                tu.is_owner,
                tu.created_at
            order by tu.is_owner desc, u.email asc
            """
        ),
        {"tenant_id": tenant_id},
    )

    users: list[TenantUserSummary] = []
    for row in result.mappings():
        users.append(
            TenantUserSummary(
                user_id=str(row["user_id"]),
                email=str(row["email"]),
                full_name=row["full_name"],
                user_is_active=bool(row["user_is_active"]),
                membership_is_active=bool(row["membership_is_active"]),
                is_owner=bool(row["is_owner"]),
                role_names=list(row["role_names"] or []),
                membership_created_at=row["membership_created_at"],
            )
        )
    return users


async def provision_tenant_user(
    session: AsyncSession,
    tenant_id: str,
    email: str,
    full_name: str | None,
    password: str | None,
    role_names: tuple[str, ...] | list[str] = ("user",),
    is_owner: bool = False,
    role_ids_by_name: dict[str, str] | None = None,
) -> TenantUserProvisionResult:
    if not await _tenant_exists(session, tenant_id=tenant_id):
        raise ValueError(f"Tenant does not exist: {tenant_id}")

    normalized_role_names = _normalize_role_names(role_names)
    if is_owner and "owner" not in normalized_role_names:
        normalized_role_names.append("owner")
    if not normalized_role_names:
        raise ValueError("At least one role name must be provided")

    resolved_role_ids = role_ids_by_name or await _load_role_ids_by_name(
        session,
        tenant_id=tenant_id,
        role_names=normalized_role_names,
    )

    user = await provision_user(
        session,
        email=email,
        full_name=full_name,
        password=password,
    )
    membership = await ensure_tenant_membership(
        session,
        tenant_id=tenant_id,
        user_id=user.user_id,
        is_owner=is_owner or ("owner" in normalized_role_names),
    )

    role_assignments: list[RoleAssignmentResult] = []
    for role_name in normalized_role_names:
        role_id = resolved_role_ids.get(role_name)
        if not role_id:
            raise ValueError(f"Role is not seeded for tenant {tenant_id}: {role_name}")

        assignment = await ensure_tenant_user_role(
            session,
            tenant_id=tenant_id,
            user_id=user.user_id,
            role_id=role_id,
            role_name=role_name,
        )
        role_assignments.append(assignment)

    return TenantUserProvisionResult(
        tenant_id=tenant_id,
        user=user,
        membership=membership,
        role_assignments=role_assignments,
    )


async def provision_tenant_admin(
    session: AsyncSession,
    tenant_id: str,
    admin_email: str,
    admin_full_name: str | None,
    admin_password: str | None,
    role_names: tuple[str, ...] = ("admin",),
    is_owner: bool = False,
    seeded_rbac: RbacSeedResult | None = None,
) -> AdminProvisionResult:
    return await provision_tenant_user(
        session,
        tenant_id=tenant_id,
        email=admin_email,
        full_name=admin_full_name,
        password=admin_password,
        role_names=role_names,
        is_owner=is_owner,
        role_ids_by_name=(seeded_rbac.role_ids_by_name if seeded_rbac else None),
    )


async def assign_roles_to_tenant_user(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    role_names: tuple[str, ...] | list[str],
    is_owner: bool = False,
) -> TenantRoleAssignmentBatchResult:
    normalized_role_names = _normalize_role_names(role_names)
    if not normalized_role_names:
        raise ValueError("At least one role name must be provided")

    existing_owner_state = await _get_membership_owner_state(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    if existing_owner_state is None:
        raise ValueError(f"User is not a member of tenant {tenant_id}: {user_id}")

    promote_owner = is_owner or ("owner" in normalized_role_names)
    membership = await ensure_tenant_membership(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        is_owner=promote_owner,
    )
    resolved_role_ids = await _load_role_ids_by_name(
        session,
        tenant_id=tenant_id,
        role_names=normalized_role_names,
    )

    role_assignments: list[RoleAssignmentResult] = []
    for role_name in normalized_role_names:
        assignment = await ensure_tenant_user_role(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=resolved_role_ids[role_name],
            role_name=role_name,
        )
        role_assignments.append(assignment)

    return TenantRoleAssignmentBatchResult(
        tenant_id=tenant_id,
        user_id=user_id,
        is_owner=membership.is_owner,
        role_assignments=role_assignments,
    )


async def ensure_tenant_membership(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    is_owner: bool,
) -> MembershipProvisionResult:
    existing_owner_state = await _get_membership_owner_state(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    membership_exists = existing_owner_state is not None

    await session.execute(
        text(
            """
            insert into public.tenant_users (tenant_id, user_id, is_owner, is_active)
            values (
                cast(:tenant_id as varchar),
                cast(:user_id as varchar),
                :is_owner,
                true
            )
            on conflict (tenant_id, user_id) do update
              set is_owner = public.tenant_users.is_owner or excluded.is_owner,
                  is_active = true
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "is_owner": is_owner},
    )

    effective_is_owner = bool(existing_owner_state) or is_owner

    return MembershipProvisionResult(
        tenant_id=tenant_id,
        user_id=user_id,
        created_membership=not membership_exists,
        is_owner=effective_is_owner,
    )


async def ensure_tenant_user_role(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    role_id: str,
    role_name: str,
) -> RoleAssignmentResult:
    assignment_exists = await _tenant_user_role_exists(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
    )

    await session.execute(
        text(
            """
            insert into public.tenant_user_roles (tenant_id, user_id, role_id)
            values (
                cast(:tenant_id as varchar),
                cast(:user_id as varchar),
                cast(:role_id as varchar)
            )
            on conflict do nothing
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "role_id": role_id},
    )

    return RoleAssignmentResult(
        role_name=role_name,
        role_id=role_id,
        created_assignment=not assignment_exists,
    )


async def _tenant_exists(session: AsyncSession, tenant_id: str) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    return result.scalar_one_or_none() is not None


async def _get_membership_owner_state(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
) -> bool | None:
    result = await session.execute(
        text(
            """
            select is_owner
            from public.tenant_users
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    state = result.scalar_one_or_none()
    if state is None:
        return None
    return bool(state)


async def _tenant_user_role_exists(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    role_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.tenant_user_roles
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
              and role_id = cast(:role_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "role_id": role_id},
    )
    return result.scalar_one_or_none() is not None


async def _load_role_ids_by_name(
    session: AsyncSession,
    tenant_id: str,
    role_names: list[str],
) -> dict[str, str]:
    if not role_names:
        return {}

    result = await session.execute(
        text(
            """
            select id, name
            from public.roles
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    role_ids_by_name = {
        str(row.name): str(row.id)
        for row in result
        if str(row.name) in role_names
    }
    missing_role_names = [role_name for role_name in role_names if role_name not in role_ids_by_name]
    if missing_role_names:
        raise ValueError(
            f"Roles not found for tenant {tenant_id}: {', '.join(missing_role_names)}"
        )
    return role_ids_by_name


def _normalize_role_names(role_names: tuple[str, ...] | list[str]) -> list[str]:
    normalized: list[str] = []
    for role_name in role_names:
        cleaned = role_name.strip().lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized

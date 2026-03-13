from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.rbac_seed import DEFAULT_ROLE_PERMISSIONS, get_default_permission_rows


@dataclass(slots=True)
class RbacSeedResult:
    tenant_id: str
    permission_ids_by_code: dict[str, str] = field(default_factory=dict)
    role_ids_by_name: dict[str, str] = field(default_factory=dict)
    created_permissions: list[str] = field(default_factory=list)
    existing_permissions: list[str] = field(default_factory=list)
    created_roles: list[str] = field(default_factory=list)
    existing_roles: list[str] = field(default_factory=list)
    created_role_permissions: list[str] = field(default_factory=list)
    existing_role_permissions: list[str] = field(default_factory=list)


async def seed_default_rbac(
    session: AsyncSession,
    tenant_id: str,
) -> RbacSeedResult:
    result = RbacSeedResult(tenant_id=tenant_id)

    permission_rows = get_default_permission_rows()

    for code, description in permission_rows:
        existing_permission_id = await _get_permission_id(session, code=code)
        if existing_permission_id:
            result.existing_permissions.append(code)
        else:
            result.created_permissions.append(code)

        permission_id = await _upsert_permission(
            session=session,
            code=code,
            description=description,
        )
        result.permission_ids_by_code[code] = permission_id

    for role_name in DEFAULT_ROLE_PERMISSIONS:
        existing_role_id = await _get_role_id(
            session=session,
            tenant_id=tenant_id,
            role_name=role_name,
        )
        if existing_role_id:
            result.existing_roles.append(role_name)
        else:
            result.created_roles.append(role_name)

        role_id = await _upsert_role(
            session=session,
            tenant_id=tenant_id,
            role_name=role_name,
        )
        result.role_ids_by_name[role_name] = role_id

    for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
        role_id = result.role_ids_by_name[role_name]

        for permission_code in permission_codes:
            permission_id = result.permission_ids_by_code.get(permission_code)
            if not permission_id:
                raise ValueError(
                    f"Missing permission_id for permission_code='{permission_code}' "
                    f"while seeding role='{role_name}'"
                )

            mapping = f"{role_name}:{permission_code}"
            mapping_exists = await _role_permission_exists(
                session=session,
                role_id=role_id,
                permission_id=permission_id,
            )

            if mapping_exists:
                result.existing_role_permissions.append(mapping)
                continue

            await session.execute(
                text(
                    """
                    insert into public.role_permissions (role_id, permission_id)
                    values (cast(:role_id as varchar), cast(:permission_id as varchar))
                    on conflict do nothing
                    """
                ),
                {"role_id": role_id, "permission_id": permission_id},
            )
            result.created_role_permissions.append(mapping)

    return result


async def _get_permission_id(
    session: AsyncSession,
    code: str,
) -> str | None:
    result = await session.execute(
        text(
            """
            select id
            from public.permissions
            where code = cast(:code as varchar)
            """
        ),
        {"code": code},
    )
    permission_id = result.scalar_one_or_none()
    return str(permission_id) if permission_id else None


async def _upsert_permission(
    session: AsyncSession,
    code: str,
    description: str,
) -> str:
    result = await session.execute(
        text(
            """
            insert into public.permissions (id, code, description)
            values (
                cast(:id as varchar),
                cast(:code as varchar),
                cast(:description as varchar)
            )
            on conflict (code) do update
              set description = excluded.description
            returning id
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "code": code,
            "description": description,
        },
    )
    return str(result.scalar_one())


async def _get_role_id(
    session: AsyncSession,
    tenant_id: str,
    role_name: str,
) -> str | None:
    result = await session.execute(
        text(
            """
            select id
            from public.roles
            where tenant_id = cast(:tenant_id as varchar)
              and name = cast(:role_name as varchar)
            """
        ),
        {"tenant_id": tenant_id, "role_name": role_name},
    )
    role_id = result.scalar_one_or_none()
    return str(role_id) if role_id else None


async def _upsert_role(
    session: AsyncSession,
    tenant_id: str,
    role_name: str,
) -> str:
    result = await session.execute(
        text(
            """
            insert into public.roles (id, tenant_id, name)
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:role_name as varchar)
            )
            on conflict (tenant_id, name) do update
              set name = excluded.name
            returning id
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "role_name": role_name,
        },
    )
    return str(result.scalar_one())


async def _role_permission_exists(
    session: AsyncSession,
    role_id: str,
    permission_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.role_permissions
            where role_id = cast(:role_id as varchar)
              and permission_id = cast(:permission_id as varchar)
            """
        ),
        {"role_id": role_id, "permission_id": permission_id},
    )
    return result.scalar_one_or_none() is not None
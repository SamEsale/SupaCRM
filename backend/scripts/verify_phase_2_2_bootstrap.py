import asyncio
import json
import sys

from sqlalchemy import text

from app.db import async_session_factory, reset_tenant_guc, set_tenant_guc
from app.rbac.rbac_seed import DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS


async def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.verify_phase_2_2_bootstrap <tenant_id> <admin_email>")
        raise SystemExit(1)

    tenant_id = sys.argv[1].strip()
    admin_email = sys.argv[2].strip().lower()

    if not tenant_id:
        print("Error: tenant_id is required")
        raise SystemExit(1)

    if not admin_email:
        print("Error: admin_email is required")
        raise SystemExit(1)

    async with async_session_factory() as session:
        try:
            async with session.begin():
                await set_tenant_guc(session, tenant_id)

                tenant_row = await _get_tenant(session, tenant_id)
                admin_row = await _get_admin_identity(session, tenant_id, admin_email)
                role_rows = await _get_roles(session, tenant_id)
                permission_rows = await _get_permissions(session)
                role_permission_rows = await _get_role_permissions(session, tenant_id)
                admin_assignments = await _get_admin_role_assignments(session, tenant_id, admin_email)

                await reset_tenant_guc(session)

            expected_roles = sorted(DEFAULT_ROLE_PERMISSIONS.keys())
            actual_roles = sorted(role_rows.keys())

            expected_permissions = sorted(DEFAULT_PERMISSIONS)
            actual_permissions = sorted(permission_rows)

            missing_permissions = sorted(set(expected_permissions) - set(actual_permissions))
            extra_permissions = sorted(set(actual_permissions) - set(expected_permissions))

            expected_role_permissions = sorted(
                f"{role_name}:{permission_code}"
                for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items()
                for permission_code in permission_codes
            )
            actual_role_permissions = sorted(role_permission_rows)

            assigned_role_names = sorted(admin_assignments)

            result = {
                "tenant_exists": tenant_row is not None,
                "tenant": tenant_row,
                "admin_exists": admin_row is not None,
                "admin": admin_row,
                "roles": {
                    "expected": expected_roles,
                    "actual": actual_roles,
                    "all_present": actual_roles == expected_roles,
                },
                "permissions": {
                    "expected": expected_permissions,
                    "actual": actual_permissions,
                    "missing": missing_permissions,
                    "extra_global_permissions": extra_permissions,
                    "all_required_present": len(missing_permissions) == 0,
                },
                "role_permissions": {
                    "expected_count": len(expected_role_permissions),
                    "actual_count": len(actual_role_permissions),
                    "all_present": actual_role_permissions == expected_role_permissions,
                },
                "admin_assignments": {
                    "actual": assigned_role_names,
                    "has_admin": "admin" in assigned_role_names,
                    "has_owner": "owner" in assigned_role_names,
                },
                "phase_2_2_verified": all(
                    [
                        tenant_row is not None,
                        admin_row is not None,
                        bool(admin_row and admin_row["membership_is_active"]),
                        bool(admin_row and admin_row["is_owner"]),
                        actual_roles == expected_roles,
                        len(missing_permissions) == 0,
                        actual_role_permissions == expected_role_permissions,
                        "admin" in assigned_role_names,
                        "owner" in assigned_role_names,
                    ]
                ),
            }

            print(json.dumps(result, indent=2, default=str))
        except Exception:
            await session.rollback()
            raise


async def _get_tenant(session, tenant_id: str):
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
    return dict(row) if row else None


async def _get_admin_identity(session, tenant_id: str, admin_email: str):
    result = await session.execute(
        text(
            """
            select
                u.id as user_id,
                u.email,
                u.full_name,
                u.is_active as user_is_active,
                tu.is_active as membership_is_active,
                tu.is_owner
            from public.tenant_users tu
            join public.users u
              on u.id = tu.user_id
            where tu.tenant_id = cast(:tenant_id as varchar)
              and lower(u.email) = :admin_email
            """
        ),
        {"tenant_id": tenant_id, "admin_email": admin_email},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _get_roles(session, tenant_id: str):
    result = await session.execute(
        text(
            """
            select id, name
            from public.roles
            where tenant_id = cast(:tenant_id as varchar)
            order by name
            """
        ),
        {"tenant_id": tenant_id},
    )
    return {str(row.name): str(row.id) for row in result}


async def _get_permissions(session):
    result = await session.execute(
        text(
            """
            select code
            from public.permissions
            order by code
            """
        )
    )
    return [str(row.code) for row in result]


async def _get_role_permissions(session, tenant_id: str):
    result = await session.execute(
        text(
            """
            select r.name, p.code
            from public.role_permissions rp
            join public.roles r
              on r.id = rp.role_id
            join public.permissions p
              on p.id = rp.permission_id
            where r.tenant_id = cast(:tenant_id as varchar)
            order by r.name, p.code
            """
        ),
        {"tenant_id": tenant_id},
    )
    return [f"{row.name}:{row.code}" for row in result]


async def _get_admin_role_assignments(session, tenant_id: str, admin_email: str):
    result = await session.execute(
        text(
            """
            select r.name
            from public.tenant_user_roles tur
            join public.roles r
              on r.id = tur.role_id
             and r.tenant_id = tur.tenant_id
            join public.users u
              on u.id = tur.user_id
            where tur.tenant_id = cast(:tenant_id as varchar)
              and lower(u.email) = :admin_email
            order by r.name
            """
        ),
        {"tenant_id": tenant_id, "admin_email": admin_email},
    )
    return [str(row.name) for row in result]


if __name__ == "__main__":
    asyncio.run(main())
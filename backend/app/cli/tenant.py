import asyncio
import uuid

import typer
from argon2 import PasswordHasher
from sqlalchemy import text

from app.db import async_session_factory, set_tenant_guc

app = typer.Typer(no_args_is_help=True, help="Tenant bootstrap/seed operations")


@app.command("create")
def create_tenant(
    name: str = typer.Option(..., help="Tenant display name"),
    admin_email: str = typer.Option(..., help="Initial admin email"),
    admin_full_name: str = typer.Option("Tenant Admin", help="Initial admin full name"),
    admin_password: str | None = typer.Option(
        None,
        help="Optional initial admin password. If provided, stores Argon2 hash in user_credentials.",
        prompt=False,
        hide_input=True,
    ),
) -> None:
    asyncio.run(_create_tenant_async(name, admin_email, admin_full_name, admin_password))


async def _create_tenant_async(
    name: str,
    admin_email: str,
    admin_full_name: str,
    admin_password: str | None,
) -> None:
    tenant_id = str(uuid.uuid4())
    admin_user_id = str(uuid.uuid4())

    # Argon2 hash (only if password provided)
    password_hash: str | None = None
    if admin_password:
        ph = PasswordHasher()
        password_hash = ph.hash(admin_password)

    async with async_session_factory() as session:
        async with session.begin():
            # 1) Create tenant
            await session.execute(
                text(
                    """
                    INSERT INTO tenants (id, name, is_active)
                    VALUES (CAST(:id AS varchar), CAST(:name AS varchar), TRUE)
                    """
                ),
                {"id": tenant_id, "name": name},
            )

            # 2) Set tenant context for tenant-scoped inserts
            await set_tenant_guc(session, tenant_id)

            # 3) Ensure global permissions exist (permissions: id, code, description)
            permissions = [
                ("crm.read", "Read CRM data"),
                ("crm.write", "Write CRM data"),
                ("users.manage", "Manage users"),
                ("roles.manage", "Manage roles"),
                ("audit.read", "Read audit logs"),
            ]

            for code, desc in permissions:
                await session.execute(
                    text(
                        """
                        INSERT INTO permissions (id, code, description)
                        SELECT CAST(:id AS varchar),
                               CAST(:code AS varchar),
                               CAST(:description AS varchar)
                        WHERE NOT EXISTS (
                            SELECT 1 FROM permissions p WHERE p.code = CAST(:code AS varchar)
                        )
                        """
                    ),
                    {"id": str(uuid.uuid4()), "code": code, "description": desc},
                )

            # 4) Seed tenant roles (roles: id, tenant_id, name)
            role_ids: dict[str, str] = {}
            for rname in ("admin", "member"):
                res = await session.execute(
                    text(
                        """
                        INSERT INTO roles (id, tenant_id, name)
                        VALUES (CAST(:id AS varchar), CAST(:tenant_id AS varchar), CAST(:name AS varchar))
                        ON CONFLICT (tenant_id, name) DO UPDATE
                          SET name = EXCLUDED.name
                        RETURNING id
                        """
                    ),
                    {"id": str(uuid.uuid4()), "tenant_id": tenant_id, "name": rname},
                )
                role_ids[rname] = str(res.scalar_one())

            # 5) Attach permissions to roles (role_permissions: role_id, permission_id)
            # Admin gets all permissions
            await session.execute(
                text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT CAST(:admin_role_id AS varchar), p.id
                    FROM permissions p
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"admin_role_id": role_ids["admin"]},
            )

            # Member gets minimal subset
            await session.execute(
                text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT CAST(:member_role_id AS varchar), p.id
                    FROM permissions p
                    WHERE p.code IN ('crm.read', 'audit.read')
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"member_role_id": role_ids["member"]},
            )

            # 6) Create admin user (users has no password fields)
            await session.execute(
                text(
                    """
                    INSERT INTO users (id, email, full_name, is_active, is_superuser)
                    VALUES (CAST(:id AS varchar), CAST(:email AS varchar), CAST(:full_name AS varchar), TRUE, FALSE)
                    """
                ),
                {"id": admin_user_id, "email": admin_email, "full_name": admin_full_name},
            )

            # 6b) Store admin password hash (optional)
            if password_hash:
                await session.execute(
                    text(
                        """
                        INSERT INTO user_credentials (user_id, password_hash, is_password_set)
                        VALUES (CAST(:user_id AS varchar), CAST(:password_hash AS text), TRUE)
                        ON CONFLICT (user_id) DO UPDATE
                          SET password_hash = EXCLUDED.password_hash,
                              is_password_set = TRUE,
                              updated_at = now()
                        """
                    ),
                    {"user_id": admin_user_id, "password_hash": password_hash},
                )
            else:
                # Ensure a row exists marking password not set (optional but useful)
                await session.execute(
                    text(
                        """
                        INSERT INTO user_credentials (user_id, password_hash, is_password_set)
                        VALUES (CAST(:user_id AS varchar), CAST('' AS text), FALSE)
                        ON CONFLICT (user_id) DO UPDATE
                          SET is_password_set = FALSE,
                              updated_at = now()
                        """
                    ),
                    {"user_id": admin_user_id},
                )

            # 7) Link user to tenant
            await session.execute(
                text(
                    """
                    INSERT INTO tenant_users (tenant_id, user_id, is_owner, is_active)
                    VALUES (CAST(:tenant_id AS varchar), CAST(:user_id AS varchar), TRUE, TRUE)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"tenant_id": tenant_id, "user_id": admin_user_id},
            )

            # 8) Assign admin role
            await session.execute(
                text(
                    """
                    INSERT INTO tenant_user_roles (tenant_id, user_id, role_id)
                    VALUES (CAST(:tenant_id AS varchar), CAST(:user_id AS varchar), CAST(:role_id AS varchar))
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"tenant_id": tenant_id, "user_id": admin_user_id, "role_id": role_ids["admin"]},
            )

    typer.echo(f"✅ Created tenant '{name}' tenant_id={tenant_id}")
    typer.echo(f"✅ Created admin user email={admin_email} user_id={admin_user_id}")
    if admin_password:
        typer.echo("✅ Admin password stored in user_credentials (argon2 hash)")
    else:
        typer.echo("⚠️  No admin password provided; user_credentials marked is_password_set=false")

import asyncio

import typer

from app.db_admin import AdminSessionLocal
from app.rbac.service import seed_default_rbac
from app.tenants.service import bootstrap_tenant, ensure_tenant, provision_tenant_admin

app = typer.Typer(no_args_is_help=True)


@app.command("create")
def create_tenant(
    tenant_id: str = typer.Option(..., help="Stable tenant identifier"),
    name: str = typer.Option(..., help="Tenant display name"),
    admin_email: str = typer.Option(..., help="Initial admin email"),
    admin_full_name: str = typer.Option("Tenant Admin", help="Initial admin full name"),
    admin_password: str | None = typer.Option(
        None,
        help="Optional initial admin password. If omitted, password auth stays disabled.",
        prompt=False,
        hide_input=True,
    ),
) -> None:
    asyncio.run(_create_tenant_async(tenant_id, name, admin_email, admin_full_name, admin_password))


async def _create_tenant_async(
    tenant_id: str,
    name: str,
    admin_email: str,
    admin_full_name: str,
    admin_password: str | None,
) -> None:
    async with AdminSessionLocal() as session:
        async with session.begin():
            result = await bootstrap_tenant(
                session,
                tenant_id=tenant_id,
                tenant_name=name,
                admin_email=admin_email,
                admin_full_name=admin_full_name,
                admin_password=admin_password,
            )

    typer.echo(
        f"tenant_id={result.tenant.tenant_id} tenant_created={result.tenant.created_tenant} "
        f"admin_user_id={result.admin.user.user_id}"
    )
    typer.echo(
        f"assigned_roles={','.join(assignment.role_name for assignment in result.admin.role_assignments)} "
        f"password_set={result.admin.user.password_set}"
    )


@app.command("seed-rbac")
def seed_rbac(
    tenant_id: str = typer.Option(..., help="Tenant identifier"),
    tenant_name: str | None = typer.Option(None, help="Optional tenant name to ensure before seeding"),
) -> None:
    asyncio.run(_seed_rbac_async(tenant_id=tenant_id, tenant_name=tenant_name))


async def _seed_rbac_async(tenant_id: str, tenant_name: str | None) -> None:
    async with AdminSessionLocal() as session:
        async with session.begin():
            if tenant_name:
                await ensure_tenant(
                    session,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                )
            result = await seed_default_rbac(session, tenant_id=tenant_id)

    typer.echo(
        f"tenant_id={tenant_id} created_roles={','.join(result.created_roles) or '-'} "
        f"created_permissions={','.join(result.created_permissions) or '-'}"
    )


@app.command("create-admin-user")
def create_admin_user(
    tenant_id: str = typer.Option(..., help="Tenant identifier"),
    email: str = typer.Option(..., help="Admin email"),
    full_name: str = typer.Option("Tenant Admin", help="Admin full name"),
    password: str | None = typer.Option(
        None,
        help="Optional password. If omitted, password auth stays disabled.",
        prompt=False,
        hide_input=True,
    ),
    owner: bool = typer.Option(False, help="Also mark the user as owner and assign owner role"),
) -> None:
    asyncio.run(
        _create_admin_user_async(
            tenant_id=tenant_id,
            email=email,
            full_name=full_name,
            password=password,
            owner=owner,
        )
    )


async def _create_admin_user_async(
    tenant_id: str,
    email: str,
    full_name: str,
    password: str | None,
    owner: bool,
) -> None:
    role_names = ("admin", "owner") if owner else ("admin",)

    async with AdminSessionLocal() as session:
        async with session.begin():
            result = await provision_tenant_admin(
                session,
                tenant_id=tenant_id,
                admin_email=email,
                admin_full_name=full_name,
                admin_password=password,
                role_names=role_names,
                is_owner=owner,
            )

    typer.echo(
        f"user_id={result.user.user_id} email={result.user.email} "
        f"assigned_roles={','.join(assignment.role_name for assignment in result.role_assignments)}"
    )

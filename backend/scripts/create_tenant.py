import asyncio
import json
import sys

from app.db import async_session_factory
from app.rbac.service import seed_default_rbac
from app.tenants.service import ensure_tenant


async def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.create_tenant <tenant_id> <tenant_name>")
        raise SystemExit(1)

    tenant_id = sys.argv[1].strip()
    tenant_name = sys.argv[2].strip()

    if not tenant_id:
        print("Error: tenant_id is required")
        raise SystemExit(1)

    if not tenant_name:
        print("Error: tenant_name is required")
        raise SystemExit(1)

    async with async_session_factory() as session:
        try:
            async with session.begin():
                tenant = await ensure_tenant(
                    session,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                )
                rbac = await seed_default_rbac(session, tenant_id=tenant_id)

            print(
                json.dumps(
                    {
                        "tenant": {
                            "tenant_id": tenant.tenant_id,
                            "tenant_name": tenant.tenant_name,
                            "created_tenant": tenant.created_tenant,
                        },
                        "rbac": {
                            "created_permissions": rbac.created_permissions,
                            "existing_permissions": rbac.existing_permissions,
                            "created_roles": rbac.created_roles,
                            "existing_roles": rbac.existing_roles,
                            "created_role_permissions": rbac.created_role_permissions,
                            "existing_role_permissions": rbac.existing_role_permissions,
                        },
                    },
                    indent=2,
                )
            )
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
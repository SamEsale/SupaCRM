import asyncio
import json
import sys

from app.db import async_session_factory, reset_tenant_guc, set_tenant_guc
from app.rbac.service import seed_default_rbac


async def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.seed_rbac <tenant_id>")
        raise SystemExit(1)

    tenant_id = sys.argv[1].strip()
    if not tenant_id:
        print("Error: tenant_id is required")
        raise SystemExit(1)

    async with async_session_factory() as session:
        try:
            async with session.begin():
                await set_tenant_guc(session, tenant_id)
                result = await seed_default_rbac(session, tenant_id=tenant_id)
                await reset_tenant_guc(session)

            print(
                json.dumps(
                    {
                        "tenant_id": result.tenant_id,
                        "created_permissions": result.created_permissions,
                        "existing_permissions": result.existing_permissions,
                        "created_roles": result.created_roles,
                        "existing_roles": result.existing_roles,
                        "created_role_permissions": result.created_role_permissions,
                        "existing_role_permissions": result.existing_role_permissions,
                    },
                    indent=2,
                )
            )
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
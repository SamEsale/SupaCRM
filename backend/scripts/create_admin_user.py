import asyncio
import json
import sys

from app.db import async_session_factory, reset_tenant_guc, set_tenant_guc
from app.rbac.service import seed_default_rbac
from app.tenants.service import provision_tenant_admin


async def main() -> None:
    if len(sys.argv) not in (5, 6):
        print(
            "Usage: python -m scripts.create_admin_user "
            "<tenant_id> <admin_email> <admin_full_name> <admin_password> [is_owner]"
        )
        raise SystemExit(1)

    tenant_id = sys.argv[1].strip()
    admin_email = sys.argv[2].strip()
    admin_full_name = sys.argv[3].strip()
    admin_password = sys.argv[4]
    is_owner = True

    if len(sys.argv) == 6:
        is_owner = sys.argv[5].strip().lower() in {"1", "true", "yes", "y"}

    if not tenant_id:
        print("Error: tenant_id is required")
        raise SystemExit(1)

    if not admin_email:
        print("Error: admin_email is required")
        raise SystemExit(1)

    if not admin_full_name:
        print("Error: admin_full_name is required")
        raise SystemExit(1)

    if not admin_password:
        print("Error: admin_password is required")
        raise SystemExit(1)

    async with async_session_factory() as session:
        try:
            async with session.begin():
                await set_tenant_guc(session, tenant_id)
                seeded_rbac = await seed_default_rbac(session, tenant_id=tenant_id)
                result = await provision_tenant_admin(
                    session,
                    tenant_id=tenant_id,
                    admin_email=admin_email,
                    admin_full_name=admin_full_name,
                    admin_password=admin_password,
                    role_names=("admin",),
                    is_owner=is_owner,
                    seeded_rbac=seeded_rbac,
                )
                await reset_tenant_guc(session)

            print(
                json.dumps(
                    {
                        "tenant_id": result.tenant_id,
                        "user": {
                            "user_id": result.user.user_id,
                            "email": result.user.email,
                            "created_user": result.user.created_user,
                            "created_credentials": result.user.created_credentials,
                            "password_set": result.user.password_set,
                        },
                        "membership": {
                            "created_membership": result.membership.created_membership,
                            "is_owner": result.membership.is_owner,
                        },
                        "role_assignments": [
                            {
                                "role_name": assignment.role_name,
                                "role_id": assignment.role_id,
                                "created_assignment": assignment.created_assignment,
                            }
                            for assignment in result.role_assignments
                        ],
                    },
                    indent=2,
                )
            )
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
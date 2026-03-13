from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db_admin import AdminSessionLocal
from app.tenants.service import bootstrap_tenant


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a tenant bootstrap state.")
    parser.add_argument("--tenant-id", required=True, help="Stable tenant identifier")
    parser.add_argument("--tenant-name", required=True, help="Tenant display name")
    parser.add_argument("--admin-email", required=True, help="Initial admin email")
    parser.add_argument("--admin-full-name", default="Tenant Admin", help="Initial admin full name")
    parser.add_argument(
        "--admin-password",
        default=None,
        help="Optional initial admin password. If omitted, the account is created with password disabled.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    async with AdminSessionLocal() as session:
        async with session.begin():
            result = await bootstrap_tenant(
                session,
                tenant_id=args.tenant_id,
                tenant_name=args.tenant_name,
                admin_email=args.admin_email,
                admin_full_name=args.admin_full_name,
                admin_password=args.admin_password,
            )

    print(f"tenant_id={result.tenant.tenant_id}")
    print(f"tenant_name={result.tenant.tenant_name}")
    print(f"tenant_created={result.tenant.created_tenant}")
    print(f"admin_user_id={result.admin.user.user_id}")
    print(f"admin_email={result.admin.user.email}")
    print(f"admin_user_created={result.admin.user.created_user}")
    print(f"credentials_created={result.admin.user.created_credentials}")
    print(f"password_set={result.admin.user.password_set}")
    print(f"membership_created={result.admin.membership.created_membership}")
    print(f"is_owner={result.admin.membership.is_owner}")
    print(f"created_roles={','.join(result.rbac.created_roles) or '-'}")
    print(f"existing_roles={','.join(result.rbac.existing_roles) or '-'}")
    print(f"created_permissions={','.join(result.rbac.created_permissions) or '-'}")
    print(f"existing_permissions={','.join(result.rbac.existing_permissions) or '-'}")
    assigned_roles = ",".join(assignment.role_name for assignment in result.admin.role_assignments) or "-"
    print(f"assigned_roles={assigned_roles}")


if __name__ == "__main__":
    asyncio.run(main())

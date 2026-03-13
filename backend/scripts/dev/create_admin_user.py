from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db_admin import AdminSessionLocal
from app.tenants.service import provision_tenant_admin


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update an admin user for a tenant.")
    parser.add_argument("--tenant-id", required=True, help="Tenant identifier")
    parser.add_argument("--email", required=True, help="Admin user email")
    parser.add_argument("--full-name", default="Tenant Admin", help="Admin user full name")
    parser.add_argument(
        "--password",
        default=None,
        help="Optional password. If omitted, the account is created with password disabled.",
    )
    parser.add_argument(
        "--owner",
        action="store_true",
        help="Also mark the user as owner and assign the owner role.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    role_names = ("admin", "owner") if args.owner else ("admin",)

    async with AdminSessionLocal() as session:
        async with session.begin():
            result = await provision_tenant_admin(
                session,
                tenant_id=args.tenant_id,
                admin_email=args.email,
                admin_full_name=args.full_name,
                admin_password=args.password,
                role_names=role_names,
                is_owner=args.owner,
            )

    print(f"tenant_id={result.tenant_id}")
    print(f"user_id={result.user.user_id}")
    print(f"email={result.user.email}")
    print(f"user_created={result.user.created_user}")
    print(f"credentials_created={result.user.created_credentials}")
    print(f"password_set={result.user.password_set}")
    print(f"membership_created={result.membership.created_membership}")
    print(f"is_owner={result.membership.is_owner}")
    print(f"assigned_roles={','.join(assignment.role_name for assignment in result.role_assignments) or '-'}")
    print(
        "created_role_assignments="
        f"{','.join(assignment.role_name for assignment in result.role_assignments if assignment.created_assignment) or '-'}"
    )


if __name__ == "__main__":
    asyncio.run(main())

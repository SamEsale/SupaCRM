from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db_admin import AdminSessionLocal
from app.rbac.service import seed_default_rbac
from app.tenants.service import ensure_tenant


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed default RBAC roles and permissions for an existing tenant.")
    parser.add_argument("--tenant-id", required=True, help="Tenant identifier")
    parser.add_argument(
        "--tenant-name",
        default=None,
        help="Optional tenant name. If provided, the tenant record is also ensured before RBAC seeding.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    async with AdminSessionLocal() as session:
        async with session.begin():
            if args.tenant_name:
                await ensure_tenant(
                    session,
                    tenant_id=args.tenant_id,
                    tenant_name=args.tenant_name,
                )

            result = await seed_default_rbac(session, tenant_id=args.tenant_id)

    print(f"tenant_id={result.tenant_id}")
    print(f"created_roles={','.join(result.created_roles) or '-'}")
    print(f"existing_roles={','.join(result.existing_roles) or '-'}")
    print(f"created_permissions={','.join(result.created_permissions) or '-'}")
    print(f"existing_permissions={','.join(result.existing_permissions) or '-'}")
    print(f"created_role_permissions={','.join(result.created_role_permissions) or '-'}")
    print(f"existing_role_permissions={','.join(result.existing_role_permissions) or '-'}")


if __name__ == "__main__":
    asyncio.run(main())

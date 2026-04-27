import asyncio
import json
import uuid

from httpx import ASGITransport, AsyncClient

from app.auth.service import login_user
from app.db import async_session_factory, reset_tenant_guc, set_tenant_guc
from app.main import app
from app.tenants.service import bootstrap_tenant, provision_tenant_user


async def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    tenant_id = f"rbacverify-{suffix}"
    tenant_name = f"RBAC Verify {suffix}"

    admin_email = f"admin+{suffix}@example.test"
    user_email = f"user+{suffix}@example.test"
    password = "StrongPass123!"

    result: dict = {
        "tenant_id": tenant_id,
        "admin_email": admin_email,
        "user_email": user_email,
        "admin_login": None,
        "user_login": None,
        "admin_get_tenant": None,
        "user_get_tenant": None,
        "phase_2_4_tenant_route_auth_verified": False,
    }

    async with async_session_factory() as session:
        try:
            async with session.begin():
                bootstrap = await bootstrap_tenant(
                    session,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    admin_email=admin_email,
                    admin_full_name="Tenant Admin",
                    admin_password=password,
                )

                await set_tenant_guc(session, tenant_id)
                await provision_tenant_user(
                    session,
                    tenant_id=tenant_id,
                    email=user_email,
                    full_name="Tenant User",
                    password=password,
                    role_names=("user",),
                    is_owner=False,
                    role_ids_by_name=bootstrap.rbac.role_ids_by_name,
                )
                await reset_tenant_guc(session)
        except Exception:
            await session.rollback()
            raise

    admin_tokens = await login_user(
        tenant_id=tenant_id,
        email=admin_email,
        password=password,
        ip_address="127.0.0.1",
        user_agent="verify_phase_2_4_tenant_route_auth.py",
        request_id="phase-2-4-admin-login",
    )
    result["admin_login"] = {"ok": True}

    user_tokens = await login_user(
        tenant_id=tenant_id,
        email=user_email,
        password=password,
        ip_address="127.0.0.1",
        user_agent="verify_phase_2_4_tenant_route_auth.py",
        request_id="phase-2-4-user-login",
    )
    result["user_login"] = {"ok": True}

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        admin_response = await client.get(
            "/tenants/me",
            headers={
                "Authorization": f"Bearer {admin_tokens.access_token}",
                "X-Tenant-Id": tenant_id,
            },
        )
        result["admin_get_tenant"] = {
            "status_code": admin_response.status_code,
            "ok": admin_response.status_code == 200,
            "body": admin_response.json(),
        }

        user_response = await client.get(
            "/tenants/me",
            headers={
                "Authorization": f"Bearer {user_tokens.access_token}",
                "X-Tenant-Id": tenant_id,
            },
        )
        result["user_get_tenant"] = {
            "status_code": user_response.status_code,
            "ok": user_response.status_code == 403,
            "body": user_response.json(),
        }

    result["phase_2_4_tenant_route_auth_verified"] = all(
        [
            result["admin_login"]["ok"],
            result["user_login"]["ok"],
            result["admin_get_tenant"]["ok"],
            result["user_get_tenant"]["ok"],
        ]
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
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
    tenant_id = f"usermatrix-{suffix}"
    tenant_name = f"User Matrix {suffix}"

    admin_email = f"admin+{suffix}@example.test"
    user_email = f"user+{suffix}@example.test"
    password = "StrongPass123!"

    result: dict = {
        "tenant_id": tenant_id,
        "user_email": user_email,
        "user_login": None,
        "crm_probe": None,
        "sales_probe": None,
        "support_probe": None,
        "reporting_probe": None,
        "tenant_admin_probe": None,
        "phase_2_4_user_role_matrix_verified": False,
    }

    async with async_session_factory() as session:
        try:
            async with session.begin():
                bootstrap = await bootstrap_tenant(
                    session,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    admin_email=admin_email,
                    admin_full_name="Matrix Admin",
                    admin_password=password,
                )

                await set_tenant_guc(session, tenant_id)
                await provision_tenant_user(
                    session,
                    tenant_id=tenant_id,
                    email=user_email,
                    full_name="Matrix User",
                    password=password,
                    role_names=("user",),
                    is_owner=False,
                    role_ids_by_name=bootstrap.rbac.role_ids_by_name,
                )
                await reset_tenant_guc(session)
        except Exception:
            await session.rollback()
            raise

    user_tokens = await login_user(
        tenant_id=tenant_id,
        email=user_email,
        password=password,
        ip_address="127.0.0.1",
        user_agent="verify_phase_2_4_user_role_matrix.py",
        request_id="phase-2-4-user-matrix-login",
    )
    result["user_login"] = {"ok": True}

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = {
            "Authorization": f"Bearer {user_tokens.access_token}",
            "X-Tenant-Id": tenant_id,
        }

        crm_response = await client.get("/crm/probe", headers=headers)
        result["crm_probe"] = {
            "status_code": crm_response.status_code,
            "ok": crm_response.status_code == 200,
            "body": crm_response.json(),
        }

        sales_response = await client.get("/sales/probe", headers=headers)
        result["sales_probe"] = {
            "status_code": sales_response.status_code,
            "ok": sales_response.status_code == 200,
            "body": sales_response.json(),
        }

        support_response = await client.get("/support/probe", headers=headers)
        result["support_probe"] = {
            "status_code": support_response.status_code,
            "ok": support_response.status_code == 200,
            "body": support_response.json(),
        }

        reporting_response = await client.get("/reporting/probe", headers=headers)
        result["reporting_probe"] = {
            "status_code": reporting_response.status_code,
            "ok": reporting_response.status_code == 403,
            "body": reporting_response.json(),
        }

        tenant_response = await client.get("/tenants/me", headers=headers)
        result["tenant_admin_probe"] = {
            "status_code": tenant_response.status_code,
            "ok": tenant_response.status_code == 403,
            "body": tenant_response.json(),
        }

    result["phase_2_4_user_role_matrix_verified"] = all(
        [
            result["user_login"]["ok"],
            result["crm_probe"]["ok"],
            result["sales_probe"]["ok"],
            result["support_probe"]["ok"],
            result["reporting_probe"]["ok"],
            result["tenant_admin_probe"]["ok"],
        ]
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
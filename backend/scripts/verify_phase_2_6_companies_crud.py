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
    tenant_id = f"companies-{suffix}"
    tenant_name = f"Companies Verify {suffix}"

    admin_email = f"admin+{suffix}@example.com"
    user_email = f"user+{suffix}@example.com"
    password = "StrongPass123!"

    result: dict = {
        "tenant_id": tenant_id,
        "admin_email": admin_email,
        "user_email": user_email,
        "admin_login": None,
        "user_login": None,
        "admin_create_company": None,
        "admin_list_companies": None,
        "admin_get_company": None,
        "admin_update_company": None,
        "user_list_companies": None,
        "user_get_company": None,
        "user_create_company_denied": None,
        "user_update_company_denied": None,
        "phase_2_6_companies_crud_verified": False,
    }

    async with async_session_factory() as session:
        try:
            async with session.begin():
                bootstrap = await bootstrap_tenant(
                    session,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    admin_email=admin_email,
                    admin_full_name="Companies Admin",
                    admin_password=password,
                )

                await set_tenant_guc(session, tenant_id)
                await provision_tenant_user(
                    session,
                    tenant_id=tenant_id,
                    email=user_email,
                    full_name="Companies User",
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
        user_agent="verify_phase_2_6_companies_crud.py",
        request_id="phase-2-6-companies-admin-login",
    )
    result["admin_login"] = {"ok": True}

    user_tokens = await login_user(
        tenant_id=tenant_id,
        email=user_email,
        password=password,
        ip_address="127.0.0.1",
        user_agent="verify_phase_2_6_companies_crud.py",
        request_id="phase-2-6-companies-user-login",
    )
    result["user_login"] = {"ok": True}

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        admin_headers = {
            "Authorization": f"Bearer {admin_tokens.access_token}",
            "X-Tenant-Id": tenant_id,
        }
        user_headers = {
            "Authorization": f"Bearer {user_tokens.access_token}",
            "X-Tenant-Id": tenant_id,
        }

        create_response = await client.post(
            "/crm/companies",
            headers=admin_headers,
            json={
                "name": f"Acme {suffix}",
                "website": f"https://acme-{suffix}.example.com",
                "email": f"hello+{suffix}@example.com",
                "phone": "+46700000002",
                "industry": "Manufacturing",
                "notes": "Created by admin in verification flow",
            },
        )
        result["admin_create_company"] = {
            "status_code": create_response.status_code,
            "ok": create_response.status_code == 200,
            "body": create_response.json(),
        }

        company_id = None
        if create_response.status_code == 200:
            company_id = create_response.json().get("id")

        list_response = await client.get(
            "/crm/companies",
            headers=admin_headers,
        )
        result["admin_list_companies"] = {
            "status_code": list_response.status_code,
            "ok": list_response.status_code == 200 and list_response.json().get("total", 0) >= 1,
            "body": list_response.json(),
        }

        if company_id:
            get_response = await client.get(
                f"/crm/companies/{company_id}",
                headers=admin_headers,
            )
            result["admin_get_company"] = {
                "status_code": get_response.status_code,
                "ok": get_response.status_code == 200,
                "body": get_response.json(),
            }

            update_response = await client.patch(
                f"/crm/companies/{company_id}",
                headers=admin_headers,
                json={
                    "industry": "Industrial Procurement",
                    "notes": "Updated by admin in verification flow",
                },
            )
            result["admin_update_company"] = {
                "status_code": update_response.status_code,
                "ok": update_response.status_code == 200,
                "body": update_response.json(),
            }

            user_get_response = await client.get(
                f"/crm/companies/{company_id}",
                headers=user_headers,
            )
            result["user_get_company"] = {
                "status_code": user_get_response.status_code,
                "ok": user_get_response.status_code == 200,
                "body": user_get_response.json(),
            }

            user_update_response = await client.patch(
                f"/crm/companies/{company_id}",
                headers=user_headers,
                json={
                    "notes": "User should not be allowed to update this",
                },
            )
            result["user_update_company_denied"] = {
                "status_code": user_update_response.status_code,
                "ok": user_update_response.status_code == 403,
                "body": user_update_response.json(),
            }
        else:
            result["admin_get_company"] = {
                "ok": False,
                "detail": "Company was not created, so get-by-id was skipped.",
            }
            result["admin_update_company"] = {
                "ok": False,
                "detail": "Company was not created, so update was skipped.",
            }
            result["user_get_company"] = {
                "ok": False,
                "detail": "Company was not created, so user read was skipped.",
            }
            result["user_update_company_denied"] = {
                "ok": False,
                "detail": "Company was not created, so user update denial was skipped.",
            }

        user_list_response = await client.get(
            "/crm/companies",
            headers=user_headers,
        )
        result["user_list_companies"] = {
            "status_code": user_list_response.status_code,
            "ok": user_list_response.status_code == 200,
            "body": user_list_response.json(),
        }

        user_create_response = await client.post(
            "/crm/companies",
            headers=user_headers,
            json={
                "name": f"Blocked {suffix}",
                "website": "https://blocked.example.com",
            },
        )
        result["user_create_company_denied"] = {
            "status_code": user_create_response.status_code,
            "ok": user_create_response.status_code == 403,
            "body": user_create_response.json(),
        }

    result["phase_2_6_companies_crud_verified"] = all(
        [
            result["admin_login"]["ok"],
            result["user_login"]["ok"],
            result["admin_create_company"]["ok"],
            result["admin_list_companies"]["ok"],
            result["admin_get_company"]["ok"],
            result["admin_update_company"]["ok"],
            result["user_list_companies"]["ok"],
            result["user_get_company"]["ok"],
            result["user_create_company_denied"]["ok"],
            result["user_update_company_denied"]["ok"],
        ]
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import json
import uuid

from httpx import ASGITransport, AsyncClient

from app.auth.service import AuthFlowError, login_user
from app.core.config import settings
from app.main import app
from app.tenants.service import bootstrap_tenant


async def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    tenant_id = f"lifecycle-{suffix}"
    tenant_name = f"Lifecycle Verify {suffix}"
    admin_email = f"admin+{suffix}@example.test"
    password = "StrongPass123!"

    result: dict = {
        "tenant_id": tenant_id,
        "admin_email": admin_email,
        "baseline_login": None,
        "suspend_route": None,
        "login_while_suspended": None,
        "reactivate_route_internal": None,
        "login_after_reactivation": None,
        "disable_route_internal": None,
        "login_while_disabled": None,
        "phase_2_5_lifecycle_verified": False,
    }

    from app.db import async_session_factory

    async with async_session_factory() as session:
        try:
            async with session.begin():
                await bootstrap_tenant(
                    session,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    admin_email=admin_email,
                    admin_full_name="Lifecycle Admin",
                    admin_password=password,
                )
        except Exception:
            await session.rollback()
            raise

    admin_login = await login_user(
        tenant_id=tenant_id,
        email=admin_email,
        password=password,
        ip_address="127.0.0.1",
        user_agent="verify_phase_2_5_tenant_lifecycle.py",
        request_id="phase-2-5-baseline-login",
    )
    result["baseline_login"] = {"ok": True}

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        tenant_auth_headers = {
            "Authorization": f"Bearer {admin_login.access_token}",
            "X-Tenant-Id": tenant_id,
        }
        internal_headers = {
            "X-Bootstrap-Key": settings.BOOTSTRAP_API_KEY,
        }

        suspend_response = await client.patch(
            "/tenants/me/status",
            headers=tenant_auth_headers,
            json={
                "status": "suspended",
                "status_reason": "Verification suspension",
            },
        )
        result["suspend_route"] = {
            "status_code": suspend_response.status_code,
            "ok": suspend_response.status_code == 200,
            "body": suspend_response.json(),
        }

        result["login_while_suspended"] = await _attempt_login_expect_failure(
            tenant_id=tenant_id,
            email=admin_email,
            password=password,
            request_id="phase-2-5-login-suspended",
        )

        reactivate_response = await client.patch(
            f"/internal/bootstrap/tenants/{tenant_id}/status",
            headers=internal_headers,
            json={
                "status": "active",
                "status_reason": "Verification reactivation",
            },
        )
        result["reactivate_route_internal"] = {
            "status_code": reactivate_response.status_code,
            "ok": reactivate_response.status_code == 200,
            "body": reactivate_response.json(),
        }

        try:
            reactivated_login = await login_user(
                tenant_id=tenant_id,
                email=admin_email,
                password=password,
                ip_address="127.0.0.1",
                user_agent="verify_phase_2_5_tenant_lifecycle.py",
                request_id="phase-2-5-login-reactivated",
            )
            result["login_after_reactivation"] = {
                "ok": True,
                "access_token_expires_at": reactivated_login.access_token_expires_at.isoformat(),
            }
        except AuthFlowError as exc:
            result["login_after_reactivation"] = {
                "ok": False,
                "status_code": int(exc.status_code),
                "detail": exc.detail,
            }

        disable_response = await client.patch(
            f"/internal/bootstrap/tenants/{tenant_id}/status",
            headers=internal_headers,
            json={
                "status": "disabled",
                "status_reason": "Verification disable",
            },
        )
        result["disable_route_internal"] = {
            "status_code": disable_response.status_code,
            "ok": disable_response.status_code == 200,
            "body": disable_response.json(),
        }

        result["login_while_disabled"] = await _attempt_login_expect_failure(
            tenant_id=tenant_id,
            email=admin_email,
            password=password,
            request_id="phase-2-5-login-disabled",
        )

    result["phase_2_5_lifecycle_verified"] = all(
        [
            result["baseline_login"]["ok"],
            result["suspend_route"]["ok"],
            result["login_while_suspended"]["ok"],
            result["reactivate_route_internal"]["ok"],
            result["login_after_reactivation"]["ok"],
            result["disable_route_internal"]["ok"],
            result["login_while_disabled"]["ok"],
        ]
    )

    print(json.dumps(result, indent=2, default=str))


async def _attempt_login_expect_failure(
    *,
    tenant_id: str,
    email: str,
    password: str,
    request_id: str,
) -> dict:
    try:
        await login_user(
            tenant_id=tenant_id,
            email=email,
            password=password,
            ip_address="127.0.0.1",
            user_agent="verify_phase_2_5_tenant_lifecycle.py",
            request_id=request_id,
        )
        return {
            "ok": False,
            "detail": "Expected login failure, but login succeeded.",
        }
    except AuthFlowError as exc:
        return {
            "ok": int(exc.status_code) == 401,
            "status_code": int(exc.status_code),
            "detail": exc.detail,
        }


if __name__ == "__main__":
    asyncio.run(main())
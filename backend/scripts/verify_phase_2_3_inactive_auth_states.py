import asyncio
import json
import sys
import uuid

from sqlalchemy import text

from app.auth.service import AuthFlowError, login_user
from app.db import async_session_factory, reset_tenant_guc, set_tenant_guc
from app.rbac.service import seed_default_rbac
from app.tenants.service import bootstrap_tenant


async def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: python -m scripts.verify_phase_2_3_inactive_auth_states "
            "<tenant_id_prefix> <email_prefix> <password>"
        )
        raise SystemExit(1)

    tenant_prefix = sys.argv[1].strip().lower()
    email_prefix = sys.argv[2].strip().lower()
    password = sys.argv[3]

    if not tenant_prefix:
        print("Error: tenant_id_prefix is required")
        raise SystemExit(1)

    if not email_prefix:
        print("Error: email_prefix is required")
        raise SystemExit(1)

    if not password:
        print("Error: password is required")
        raise SystemExit(1)

    suffix = uuid.uuid4().hex[:8]
    tenant_id = f"{tenant_prefix}-{suffix}"
    tenant_name = f"Auth Verify {suffix}"
    email = f"{email_prefix}+{suffix}@example.test"

    result = {
        "tenant_id": tenant_id,
        "email": email,
        "baseline_login": None,
        "inactive_membership_login": None,
        "inactive_user_login": None,
        "inactive_tenant_login": None,
        "phase_2_3_inactive_state_verified": False,
    }

    async with async_session_factory() as session:
        try:
            async with session.begin():
                bootstrap = await bootstrap_tenant(
                    session,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    admin_email=email,
                    admin_full_name="Auth Verify User",
                    admin_password=password,
                )
                await reset_tenant_guc(session)

            user_id = bootstrap.admin.user.user_id

            # 1) baseline login should succeed
            try:
                login_result = await login_user(
                    tenant_id=tenant_id,
                    email=email,
                    password=password,
                    ip_address="127.0.0.1",
                    user_agent="verify_phase_2_3_inactive_auth_states.py",
                    request_id="inactive-state-baseline",
                )
                result["baseline_login"] = {
                    "ok": True,
                    "access_token_expires_at": login_result.access_token_expires_at.isoformat(),
                }
            except AuthFlowError as exc:
                result["baseline_login"] = {
                    "ok": False,
                    "status_code": int(exc.status_code),
                    "detail": exc.detail,
                }
                print(json.dumps(result, indent=2))
                raise SystemExit(1)

            # 2) inactive membership should fail
            async with session.begin():
                await set_tenant_guc(session, tenant_id)
                await session.execute(
                    text(
                        """
                        update public.tenant_users
                        set is_active = false
                        where tenant_id = cast(:tenant_id as varchar)
                          and user_id = cast(:user_id as varchar)
                        """
                    ),
                    {"tenant_id": tenant_id, "user_id": user_id},
                )
                await reset_tenant_guc(session)

            result["inactive_membership_login"] = await _attempt_login_expect_failure(
                tenant_id=tenant_id,
                email=email,
                password=password,
                request_id="inactive-membership",
            )

            async with session.begin():
                await set_tenant_guc(session, tenant_id)
                await session.execute(
                    text(
                        """
                        update public.tenant_users
                        set is_active = true
                        where tenant_id = cast(:tenant_id as varchar)
                          and user_id = cast(:user_id as varchar)
                        """
                    ),
                    {"tenant_id": tenant_id, "user_id": user_id},
                )
                await reset_tenant_guc(session)

            # 3) inactive user should fail
            async with session.begin():
                await session.execute(
                    text(
                        """
                        update public.users
                        set is_active = false
                        where id = cast(:user_id as varchar)
                        """
                    ),
                    {"user_id": user_id},
                )

            result["inactive_user_login"] = await _attempt_login_expect_failure(
                tenant_id=tenant_id,
                email=email,
                password=password,
                request_id="inactive-user",
            )

            async with session.begin():
                await session.execute(
                    text(
                        """
                        update public.users
                        set is_active = true
                        where id = cast(:user_id as varchar)
                        """
                    ),
                    {"user_id": user_id},
                )

            # 4) inactive tenant should fail
            async with session.begin():
                await session.execute(
                    text(
                        """
                        update public.tenants
                        set is_active = false
                        where id = cast(:tenant_id as varchar)
                        """
                    ),
                    {"tenant_id": tenant_id},
                )

            result["inactive_tenant_login"] = await _attempt_login_expect_failure(
                tenant_id=tenant_id,
                email=email,
                password=password,
                request_id="inactive-tenant",
            )

            # restore tenant active for cleanliness
            async with session.begin():
                await session.execute(
                    text(
                        """
                        update public.tenants
                        set is_active = true
                        where id = cast(:tenant_id as varchar)
                        """
                    ),
                    {"tenant_id": tenant_id},
                )

            result["phase_2_3_inactive_state_verified"] = all(
                [
                    result["baseline_login"]["ok"],
                    result["inactive_membership_login"]["ok"],
                    result["inactive_user_login"]["ok"],
                    result["inactive_tenant_login"]["ok"],
                ]
            )

            print(json.dumps(result, indent=2))
        except Exception:
            await session.rollback()
            raise


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
            user_agent="verify_phase_2_3_inactive_auth_states.py",
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
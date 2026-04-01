import asyncio
import json
import sys
from http import HTTPStatus

from app.auth.service import (
    AuthFlowError,
    get_current_user_profile,
    login_user,
    logout_user,
    refresh_user_tokens,
)


async def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: python -m scripts.verify_phase_2_3_auth "
            "<tenant_id> <email> <password>"
        )
        raise SystemExit(1)

    tenant_id = sys.argv[1].strip()
    email = sys.argv[2].strip()
    password = sys.argv[3]

    if not tenant_id:
        print("Error: tenant_id is required")
        raise SystemExit(1)

    if not email:
        print("Error: email is required")
        raise SystemExit(1)

    if not password:
        print("Error: password is required")
        raise SystemExit(1)

    result: dict = {
        "tenant_id": tenant_id,
        "email": email,
        "login": None,
        "whoami": None,
        "refresh": None,
        "logout": None,
        "refresh_after_logout": None,
        "phase_2_3_core_verified": False,
    }

    login_result = None
    refresh_result = None

    try:
        login_result = await login_user(
            tenant_id=tenant_id,
            email=email,
            password=password,
            ip_address="127.0.0.1",
            user_agent="verify_phase_2_3_auth.py",
            request_id="phase-2-3-login",
        )
        result["login"] = {
            "ok": True,
            "access_token_expires_at": login_result.access_token_expires_at.isoformat(),
            "refresh_token_expires_at": login_result.refresh_token_expires_at.isoformat(),
        }
    except AuthFlowError as exc:
        result["login"] = {
            "ok": False,
            "status_code": int(exc.status_code),
            "detail": exc.detail,
        }
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    try:
        login_payload = _decode_access_payload(login_result.access_token)
        profile = await get_current_user_profile(
            tenant_id=str(login_payload["tenant_id"]),
            user_id=str(login_payload["sub"]),
        )
        result["whoami"] = {
            "ok": True,
            "user_id": profile.user_id,
            "tenant_id": profile.tenant_id,
            "email": profile.email,
            "roles": profile.roles,
            "is_owner": profile.is_owner,
            "user_is_active": profile.user_is_active,
            "membership_is_active": profile.membership_is_active,
            "tenant_is_active": profile.tenant_is_active,
        }
    except AuthFlowError as exc:
        result["whoami"] = {
            "ok": False,
            "status_code": int(exc.status_code),
            "detail": exc.detail,
        }
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    try:
        refresh_result = await refresh_user_tokens(
            refresh_token=login_result.refresh_token,
            ip_address="127.0.0.1",
            user_agent="verify_phase_2_3_auth.py",
            request_id="phase-2-3-refresh",
        )
        result["refresh"] = {
            "ok": True,
            "access_token_expires_at": refresh_result.access_token_expires_at.isoformat(),
            "refresh_token_expires_at": refresh_result.refresh_token_expires_at.isoformat(),
        }
    except AuthFlowError as exc:
        result["refresh"] = {
            "ok": False,
            "status_code": int(exc.status_code),
            "detail": exc.detail,
        }
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    try:
        refreshed_payload = _decode_access_payload(refresh_result.access_token)
        await logout_user(
            principal_user_id=str(refreshed_payload["sub"]),
            principal_tenant_id=str(refreshed_payload["tenant_id"]),
            refresh_token=refresh_result.refresh_token,
            revoke_family=True,
            ip_address="127.0.0.1",
            user_agent="verify_phase_2_3_auth.py",
            request_id="phase-2-3-logout",
        )
        result["logout"] = {
            "ok": True,
            "revoke_family": True,
        }
    except AuthFlowError as exc:
        result["logout"] = {
            "ok": False,
            "status_code": int(exc.status_code),
            "detail": exc.detail,
        }
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    try:
        await refresh_user_tokens(
            refresh_token=refresh_result.refresh_token,
            ip_address="127.0.0.1",
            user_agent="verify_phase_2_3_auth.py",
            request_id="phase-2-3-refresh-after-logout",
        )
        result["refresh_after_logout"] = {
            "ok": False,
            "detail": "Expected refresh to fail after logout, but it succeeded.",
        }
        print(json.dumps(result, indent=2))
        raise SystemExit(1)
    except AuthFlowError as exc:
        result["refresh_after_logout"] = {
            "ok": int(exc.status_code) == int(HTTPStatus.UNAUTHORIZED),
            "status_code": int(exc.status_code),
            "detail": exc.detail,
        }

    result["phase_2_3_core_verified"] = all(
        [
            result["login"]["ok"],
            result["whoami"]["ok"],
            result["refresh"]["ok"],
            result["logout"]["ok"],
            result["refresh_after_logout"]["ok"],
        ]
    )

    print(json.dumps(result, indent=2))


def _decode_access_payload(token: str) -> dict:
    from app.core.security.jwt import decode_access_token

    return decode_access_token(token)


if __name__ == "__main__":
    asyncio.run(main())
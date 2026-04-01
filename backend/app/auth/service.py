from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security.jwt import (
    TokenValidationError,
    decode_password_reset_token,
    decode_refresh_token,
    issue_access_token,
    issue_password_reset_token,
    issue_refresh_token,
)
from app.core.security.passwords import hash_password, validate_password_policy, verify_password
from app.db import async_session_factory, set_tenant_guc


@dataclass(slots=True)
class UserProvisionResult:
    user_id: str
    email: str
    created_user: bool
    created_credentials: bool
    password_set: bool


@dataclass(slots=True)
class TokenPairResult:
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


@dataclass(slots=True)
class CurrentUserProfile:
    user_id: str
    tenant_id: str
    email: str
    full_name: str | None
    roles: list[str]
    is_owner: bool
    user_is_active: bool
    membership_is_active: bool
    tenant_is_active: bool


class AuthFlowError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized:
        raise ValueError("Email is required")
    return normalized


async def ensure_user(
    session: AsyncSession,
    *,
    email: str,
    full_name: str | None,
) -> tuple[str, str, bool]:
    normalized_email = normalize_email(email)
    result = await session.execute(
        text(
            """
            select id, email
            from public.users
            where lower(email) = :email
            """
        ),
        {"email": normalized_email},
    )
    existing = result.mappings().first()
    if existing:
        await session.execute(
            text(
                """
                update public.users
                set full_name = coalesce(:full_name, full_name),
                    updated_at = now()
                where id = cast(:user_id as varchar)
                """
            ),
            {"user_id": str(existing["id"]), "full_name": full_name},
        )
        return str(existing["id"]), str(existing["email"]), False

    user_id = str(uuid.uuid4())
    await session.execute(
        text(
            """
            insert into public.users (id, email, full_name, is_active, is_superuser)
            values (
                cast(:id as varchar),
                cast(:email as varchar),
                cast(:full_name as varchar),
                true,
                false
            )
            """
        ),
        {"id": user_id, "email": normalized_email, "full_name": full_name},
    )
    return user_id, normalized_email, True


async def ensure_user_credentials(
    session: AsyncSession,
    *,
    user_id: str,
    password: str | None,
) -> tuple[bool, bool]:
    result = await session.execute(
        text(
            """
            select password_hash, is_password_set
            from public.user_credentials
            where user_id = cast(:user_id as varchar)
            """
        ),
        {"user_id": user_id},
    )
    existing = result.mappings().first()

    if existing:
        if password is None:
            return False, bool(existing["is_password_set"])

        validate_password_policy(password)
        await session.execute(
            text(
                """
                update public.user_credentials
                set password_hash = :password_hash,
                    is_password_set = true,
                    updated_at = now()
                where user_id = cast(:user_id as varchar)
                """
            ),
            {"user_id": user_id, "password_hash": hash_password(password)},
        )
        return False, True

    if password is None:
        password_hash = hash_password(str(uuid.uuid4()))
        is_password_set = False
    else:
        validate_password_policy(password)
        password_hash = hash_password(password)
        is_password_set = True

    await session.execute(
        text(
            """
            insert into public.user_credentials (
                user_id,
                password_hash,
                is_password_set
            )
            values (
                cast(:user_id as varchar),
                :password_hash,
                :is_password_set
            )
            """
        ),
        {
            "user_id": user_id,
            "password_hash": password_hash,
            "is_password_set": is_password_set,
        },
    )
    return True, is_password_set


async def provision_user(
    session: AsyncSession,
    *,
    email: str,
    full_name: str | None,
    password: str | None,
) -> UserProvisionResult:
    user_id, normalized_email, created_user = await ensure_user(
        session,
        email=email,
        full_name=full_name,
    )
    created_credentials, password_set = await ensure_user_credentials(
        session,
        user_id=user_id,
        password=password,
    )
    return UserProvisionResult(
        user_id=user_id,
        email=normalized_email,
        created_user=created_user,
        created_credentials=created_credentials,
        password_set=password_set,
    )


async def login_user(
    *,
    tenant_id: str,
    email: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> TokenPairResult:
    normalized_email = normalize_email(email)

    async with async_session_factory() as session:
        try:
            await set_tenant_guc(session, tenant_id)
            tenant = await _get_tenant_state(session, tenant_id)
            if not tenant:
                await session.rollback()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.login.failed",
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    status_code=HTTPStatus.UNAUTHORIZED,
                    message="Login failed",
                    meta={"reason": "tenant_missing", "email": normalized_email},
                )
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid credentials")

            tenant_status = str(tenant["status"])
            if tenant_status != "active":
                await session.rollback()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.login.blocked",
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    status_code=HTTPStatus.FORBIDDEN,
                    message="Login blocked by tenant lifecycle",
                    meta={
                        "reason": "tenant_not_active",
                        "tenant_status": tenant_status,
                        "email": normalized_email,
                    },
                )
                raise AuthFlowError(
                    HTTPStatus.FORBIDDEN,
                    "Tenant is not active. Access has been blocked.",
                )

            identity = await _get_identity_by_email(session, tenant_id, normalized_email)
            if not identity:
                await session.rollback()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.login.failed",
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    status_code=HTTPStatus.UNAUTHORIZED,
                    message="Login failed",
                    meta={"reason": "user_not_found", "email": normalized_email},
                )
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid credentials")

            credentials = await _get_credentials_state(session, identity["user_id"])
            if (
                not identity["user_is_active"]
                or not identity["membership_is_active"]
                or not credentials
                or not credentials["is_password_set"]
                or not credentials["password_hash"]
            ):
                await session.rollback()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.login.failed",
                    actor_user_id=identity["user_id"],
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    resource_id=identity["user_id"],
                    status_code=HTTPStatus.UNAUTHORIZED,
                    message="Login failed",
                    meta={"reason": "account_inactive_or_password_unavailable", "email": normalized_email},
                )
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid credentials")

            now = _utcnow()
            locked_until = credentials["locked_until"]
            if locked_until and locked_until > now:
                await session.rollback()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.login.failed",
                    actor_user_id=identity["user_id"],
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    resource_id=identity["user_id"],
                    status_code=HTTPStatus.UNAUTHORIZED,
                    message="Login failed",
                    meta={"reason": "account_locked", "locked_until": locked_until.isoformat()},
                )
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid credentials")

            if not verify_password(str(credentials["password_hash"]), password):
                await _record_failed_login(session, identity["user_id"], credentials, now=now)
                await session.commit()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.login.failed",
                    actor_user_id=identity["user_id"],
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    resource_id=identity["user_id"],
                    status_code=HTTPStatus.UNAUTHORIZED,
                    message="Login failed",
                    meta={"reason": "invalid_password", "email": normalized_email},
                )
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid credentials")

            roles = await _get_role_names(session, tenant_id, identity["user_id"])
            token_pair = await _issue_token_pair(
                session,
                user_id=identity["user_id"],
                tenant_id=tenant_id,
                roles=roles,
                token_version=int(credentials["refresh_token_version"]),
                user_agent=user_agent,
                ip_address=ip_address,
            )
            await _reset_login_state(session, identity["user_id"], now=now)
            await session.commit()

            await _write_audit_log(
                tenant_id=tenant_id,
                action="auth.login.succeeded",
                actor_user_id=identity["user_id"],
                actor_ip=ip_address,
                request_id=request_id,
                resource="auth",
                resource_id=identity["user_id"],
                status_code=HTTPStatus.OK,
                message="Login succeeded",
                meta={"roles": roles, "user_agent": user_agent},
            )
            return token_pair
        except AuthFlowError:
            raise
        except Exception:
            await session.rollback()
            raise


async def refresh_user_tokens(
    *,
    refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> TokenPairResult:
    try:
        payload = decode_refresh_token(refresh_token)
    except TokenValidationError as exc:
        raise AuthFlowError(HTTPStatus.UNAUTHORIZED, str(exc)) from exc

    tenant_id = str(payload["tenant_id"])
    user_id = str(payload["sub"])
    token_id = str(payload["jti"])
    family_id = str(payload["family_id"])
    token_version = int(payload["token_version"])

    async with async_session_factory() as session:
        try:
            await set_tenant_guc(session, tenant_id)
            tenant = await _get_tenant_state(session, tenant_id)
            identity = await _get_identity_by_user_id(session, tenant_id, user_id)
            credentials = await _get_credentials_state(session, user_id)
            refresh_row = await _get_refresh_token_record(session, token_id)

            if not tenant:
                await session.rollback()
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid refresh token")

            tenant_status = str(tenant["status"])
            if tenant_status != "active":
                await session.rollback()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.refresh.blocked",
                    actor_user_id=user_id,
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    resource_id=user_id,
                    status_code=HTTPStatus.FORBIDDEN,
                    message="Token refresh blocked by tenant lifecycle",
                    meta={
                        "reason": "tenant_not_active",
                        "tenant_status": tenant_status,
                        "family_id": family_id,
                    },
                )
                raise AuthFlowError(
                    HTTPStatus.FORBIDDEN,
                    "Tenant is not active. Access has been blocked.",
                )

            if (
                not identity
                or not identity["user_is_active"]
                or not identity["membership_is_active"]
                or not credentials
                or refresh_row is None
            ):
                await session.rollback()
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid refresh token")

            now = _utcnow()
            if (
                str(refresh_row["token_hash"]) != _hash_token(refresh_token)
                or refresh_row["expires_at"] <= now
                or int(credentials["refresh_token_version"]) != token_version
            ):
                await session.rollback()
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid refresh token")

            if refresh_row["revoked_at"] is not None or refresh_row["rotated_at"] is not None:
                new_version = await _increment_refresh_token_version(session, user_id)
                await _revoke_refresh_family(
                    session,
                    tenant_id=tenant_id,
                    family_id=family_id,
                    reason="refresh_token_reuse_detected",
                    now=now,
                )
                await session.commit()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.refresh.rejected",
                    actor_user_id=user_id,
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    resource_id=user_id,
                    status_code=HTTPStatus.UNAUTHORIZED,
                    message="Refresh token reuse detected",
                    meta={"family_id": family_id, "refresh_token_version": new_version},
                )
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid refresh token")

            roles = await _get_role_names(session, tenant_id, user_id)
            token_pair = await _issue_token_pair(
                session,
                user_id=user_id,
                tenant_id=tenant_id,
                roles=roles,
                token_version=token_version,
                family_id=family_id,
                user_agent=user_agent,
                ip_address=ip_address,
                replaced_token_id=token_id,
            )
            await session.commit()

            await _write_audit_log(
                tenant_id=tenant_id,
                action="auth.refresh.succeeded",
                actor_user_id=user_id,
                actor_ip=ip_address,
                request_id=request_id,
                resource="auth",
                resource_id=user_id,
                status_code=HTTPStatus.OK,
                message="Token refresh succeeded",
                meta={"family_id": family_id, "user_agent": user_agent},
            )
            return token_pair
        except AuthFlowError:
            raise
        except Exception:
            await session.rollback()
            raise


async def logout_user(
    *,
    principal_user_id: str,
    principal_tenant_id: str,
    refresh_token: str,
    revoke_family: bool,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    try:
        payload = decode_refresh_token(refresh_token)
    except TokenValidationError as exc:
        raise AuthFlowError(HTTPStatus.UNAUTHORIZED, str(exc)) from exc

    token_user_id = str(payload["sub"])
    token_tenant_id = str(payload["tenant_id"])
    token_id = str(payload["jti"])
    family_id = str(payload["family_id"])

    if token_user_id != str(principal_user_id) or token_tenant_id != str(principal_tenant_id):
        raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Refresh token does not match the authenticated user")

    async with async_session_factory() as session:
        try:
            await set_tenant_guc(session, token_tenant_id)
            refresh_row = await _get_refresh_token_record(session, token_id)
            if not refresh_row or str(refresh_row["token_hash"]) != _hash_token(refresh_token):
                await session.rollback()
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid refresh token")

            now = _utcnow()
            if revoke_family:
                await _revoke_refresh_family(
                    session,
                    tenant_id=token_tenant_id,
                    family_id=family_id,
                    reason="logout_family_revocation",
                    now=now,
                )
            else:
                await _revoke_refresh_token(
                    session,
                    tenant_id=token_tenant_id,
                    token_id=token_id,
                    reason="logout",
                    now=now,
                )
            await session.commit()

            await _write_audit_log(
                tenant_id=token_tenant_id,
                action="auth.logout.succeeded",
                actor_user_id=token_user_id,
                actor_ip=ip_address,
                request_id=request_id,
                resource="auth",
                resource_id=token_user_id,
                status_code=HTTPStatus.OK,
                message="Logout succeeded",
                meta={"family_revoked": revoke_family, "user_agent": user_agent},
            )
        except AuthFlowError:
            raise
        except Exception:
            await session.rollback()
            raise


async def initiate_password_reset(
    *,
    tenant_id: str,
    email: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> str:
    normalized_email = normalize_email(email)
    message = "If the account exists, password reset instructions have been created."

    async with async_session_factory() as session:
        try:
            await set_tenant_guc(session, tenant_id)
            tenant = await _get_tenant_state(session, tenant_id)
            identity = await _get_identity_by_email(session, tenant_id, normalized_email)
            if (
                tenant
                and tenant["is_active"]
                and identity
                and identity["user_is_active"]
                and identity["membership_is_active"]
            ):
                issued = issue_password_reset_token(subject=identity["user_id"], tenant_id=tenant_id)
                await session.execute(
                    text(
                        """
                        insert into public.password_reset_tokens (
                            id,
                            user_id,
                            tenant_id,
                            token_hash,
                            expires_at,
                            requested_ip,
                            user_agent
                        )
                        values (
                            cast(:id as varchar),
                            cast(:user_id as varchar),
                            cast(:tenant_id as varchar),
                            cast(:token_hash as varchar),
                            :expires_at,
                            cast(:requested_ip as varchar),
                            cast(:user_agent as varchar)
                        )
                        """
                    ),
                    {
                        "id": issued.jti,
                        "user_id": identity["user_id"],
                        "tenant_id": tenant_id,
                        "token_hash": _hash_token(issued.token),
                        "expires_at": issued.expires_at,
                        "requested_ip": ip_address,
                        "user_agent": user_agent,
                    },
                )
                await session.commit()
                await _write_audit_log(
                    tenant_id=tenant_id,
                    action="auth.password_reset.requested",
                    actor_user_id=identity["user_id"],
                    actor_ip=ip_address,
                    request_id=request_id,
                    resource="auth",
                    resource_id=identity["user_id"],
                    status_code=HTTPStatus.OK,
                    message="Password reset requested",
                    meta={"user_agent": user_agent},
                )
            else:
                await session.rollback()
        except Exception:
            await session.rollback()
            raise

    return message


async def complete_password_reset(
    *,
    token: str,
    new_password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    try:
        payload = decode_password_reset_token(token)
    except TokenValidationError as exc:
        raise AuthFlowError(HTTPStatus.UNAUTHORIZED, str(exc)) from exc

    validate_password_policy(new_password)

    tenant_id = str(payload["tenant_id"])
    user_id = str(payload["sub"])
    token_id = str(payload["jti"])
    token_hash = _hash_token(token)
    now = _utcnow()

    async with async_session_factory() as session:
        try:
            await set_tenant_guc(session, tenant_id)
            reset_row = await _get_password_reset_record(session, token_id)
            identity = await _get_identity_by_user_id(session, tenant_id, user_id)
            if (
                not reset_row
                or str(reset_row["token_hash"]) != token_hash
                or reset_row["used_at"] is not None
                or reset_row["expires_at"] <= now
                or not identity
            ):
                await session.rollback()
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Invalid password reset token")

            await session.execute(
                text(
                    """
                    update public.user_credentials
                    set password_hash = :password_hash,
                        is_password_set = true,
                        failed_login_attempts = 0,
                        locked_until = null,
                        refresh_token_version = refresh_token_version + 1,
                        updated_at = now()
                    where user_id = cast(:user_id as varchar)
                    """
                ),
                {"user_id": user_id, "password_hash": hash_password(new_password)},
            )
            await session.execute(
                text(
                    """
                    update public.password_reset_tokens
                    set used_at = :used_at
                    where id = cast(:token_id as varchar)
                    """
                ),
                {"token_id": token_id, "used_at": now},
            )
            await _revoke_all_user_refresh_tokens(
                session,
                tenant_id=tenant_id,
                user_id=user_id,
                reason="password_reset_completed",
                now=now,
            )
            await session.commit()

            await _write_audit_log(
                tenant_id=tenant_id,
                action="auth.password.changed",
                actor_user_id=user_id,
                actor_ip=ip_address,
                request_id=request_id,
                resource="auth",
                resource_id=user_id,
                status_code=HTTPStatus.OK,
                message="Password updated via reset flow",
                meta={"user_agent": user_agent},
            )
        except AuthFlowError:
            raise
        except Exception:
            await session.rollback()
            raise


async def get_current_user_profile(
    *,
    tenant_id: str,
    user_id: str,
) -> CurrentUserProfile:
    async with async_session_factory() as session:
        try:
            await set_tenant_guc(session, tenant_id)
            tenant = await _get_tenant_state(session, tenant_id)
            identity = await _get_identity_by_user_id(session, tenant_id, user_id)
            if not tenant or not identity:
                raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Authenticated user is no longer available")

            roles = await _get_role_names(session, tenant_id, user_id)
            return CurrentUserProfile(
                user_id=user_id,
                tenant_id=tenant_id,
                email=str(identity["email"]),
                full_name=identity["full_name"],
                roles=roles,
                is_owner=bool(identity["is_owner"]),
                user_is_active=bool(identity["user_is_active"]),
                membership_is_active=bool(identity["membership_is_active"]),
                tenant_is_active=bool(tenant["is_active"]),
            )
        except AuthFlowError:
            raise
        except Exception:
            await session.rollback()
            raise


async def _issue_token_pair(
    session: AsyncSession,
    *,
    user_id: str,
    tenant_id: str,
    roles: list[str],
    token_version: int,
    user_agent: str | None,
    ip_address: str | None,
    family_id: str | None = None,
    replaced_token_id: str | None = None,
) -> TokenPairResult:
    effective_family_id = family_id or str(uuid.uuid4())
    access_token = issue_access_token(subject=user_id, tenant_id=tenant_id, roles=roles)
    refresh_token = issue_refresh_token(
        subject=user_id,
        tenant_id=tenant_id,
        family_id=effective_family_id,
        token_version=token_version,
    )

    await session.execute(
        text(
            """
            insert into public.auth_refresh_tokens (
                id,
                user_id,
                tenant_id,
                token_hash,
                family_id,
                expires_at,
                user_agent,
                ip_address
            )
            values (
                cast(:id as varchar),
                cast(:user_id as varchar),
                cast(:tenant_id as varchar),
                cast(:token_hash as varchar),
                cast(:family_id as varchar),
                :expires_at,
                cast(:user_agent as varchar),
                cast(:ip_address as varchar)
            )
            """
        ),
        {
            "id": refresh_token.jti,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "token_hash": _hash_token(refresh_token.token),
            "family_id": effective_family_id,
            "expires_at": refresh_token.expires_at,
            "user_agent": user_agent,
            "ip_address": ip_address,
        },
    )

    if replaced_token_id:
        rotated_at = _utcnow()
        await session.execute(
            text(
                """
                update public.auth_refresh_tokens
                set rotated_at = :rotated_at,
                    last_used_at = :rotated_at,
                    replaced_by_token_id = cast(:replaced_by_token_id as varchar)
                where id = cast(:id as varchar)
                  and rotated_at is null
                  and revoked_at is null
                """
            ),
            {
                "id": replaced_token_id,
                "rotated_at": rotated_at,
                "replaced_by_token_id": refresh_token.jti,
            },
        )

    return TokenPairResult(
        access_token=access_token.token,
        refresh_token=refresh_token.token,
        access_token_expires_at=access_token.expires_at,
        refresh_token_expires_at=refresh_token.expires_at,
    )


async def _record_failed_login(
    session: AsyncSession,
    user_id: str,
    credentials: dict,
    *,
    now: datetime,
) -> None:
    failed_attempts = int(credentials["failed_login_attempts"]) + 1
    locked_until = credentials["locked_until"]
    if (not locked_until or locked_until <= now) and failed_attempts >= settings.AUTH_MAX_FAILED_ATTEMPTS:
        locked_until = now + timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)

    await session.execute(
        text(
            """
            update public.user_credentials
            set failed_login_attempts = :failed_login_attempts,
                locked_until = :locked_until,
                last_failed_login_at = :last_failed_login_at,
                updated_at = now()
            where user_id = cast(:user_id as varchar)
            """
        ),
        {
            "user_id": user_id,
            "failed_login_attempts": failed_attempts,
            "locked_until": locked_until,
            "last_failed_login_at": now,
        },
    )


async def _reset_login_state(
    session: AsyncSession,
    user_id: str,
    *,
    now: datetime,
) -> None:
    await session.execute(
        text(
            """
            update public.user_credentials
            set failed_login_attempts = 0,
                locked_until = null,
                last_login_at = :last_login_at,
                updated_at = now()
            where user_id = cast(:user_id as varchar)
            """
        ),
        {"user_id": user_id, "last_login_at": now},
    )


async def _increment_refresh_token_version(session: AsyncSession, user_id: str) -> int:
    result = await session.execute(
        text(
            """
            update public.user_credentials
            set refresh_token_version = refresh_token_version + 1,
                updated_at = now()
            where user_id = cast(:user_id as varchar)
            returning refresh_token_version
            """
        ),
        {"user_id": user_id},
    )
    new_version = result.scalar_one_or_none()
    if new_version is None:
        raise AuthFlowError(HTTPStatus.UNAUTHORIZED, "Authentication credentials are unavailable")
    return int(new_version)


async def _revoke_refresh_token(
    session: AsyncSession,
    *,
    tenant_id: str,
    token_id: str,
    reason: str,
    now: datetime,
) -> None:
    await session.execute(
        text(
            """
            update public.auth_refresh_tokens
            set revoked_at = coalesce(revoked_at, :revoked_at),
                last_used_at = coalesce(last_used_at, :revoked_at),
                revoked_reason = coalesce(revoked_reason, cast(:reason as varchar))
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:token_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "token_id": token_id,
            "revoked_at": now,
            "reason": reason,
        },
    )


async def _revoke_refresh_family(
    session: AsyncSession,
    *,
    tenant_id: str,
    family_id: str,
    reason: str,
    now: datetime,
) -> None:
    await session.execute(
        text(
            """
            update public.auth_refresh_tokens
            set revoked_at = coalesce(revoked_at, :revoked_at),
                revoked_reason = coalesce(revoked_reason, cast(:reason as varchar))
            where tenant_id = cast(:tenant_id as varchar)
              and family_id = cast(:family_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "family_id": family_id,
            "revoked_at": now,
            "reason": reason,
        },
    )


async def _revoke_all_user_refresh_tokens(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    reason: str,
    now: datetime,
) -> None:
    await session.execute(
        text(
            """
            update public.auth_refresh_tokens
            set revoked_at = coalesce(revoked_at, :revoked_at),
                revoked_reason = coalesce(revoked_reason, cast(:reason as varchar))
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "revoked_at": now,
            "reason": reason,
        },
    )


async def _get_tenant_state(session: AsyncSession, tenant_id: str) -> dict | None:
    result = await session.execute(
        text(
            """
            select id, name, status, is_active
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _get_identity_by_email(
    session: AsyncSession,
    tenant_id: str,
    email: str,
) -> dict | None:
    result = await session.execute(
        text(
            """
            select
                u.id as user_id,
                u.email,
                u.full_name,
                u.is_active as user_is_active,
                tu.is_active as membership_is_active,
                tu.is_owner
            from public.tenant_users tu
            join public.users u
              on u.id = tu.user_id
            where tu.tenant_id = cast(:tenant_id as varchar)
              and lower(u.email) = :email
            """
        ),
        {"tenant_id": tenant_id, "email": email},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _get_identity_by_user_id(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
) -> dict | None:
    result = await session.execute(
        text(
            """
            select
                u.id as user_id,
                u.email,
                u.full_name,
                u.is_active as user_is_active,
                tu.is_active as membership_is_active,
                tu.is_owner
            from public.tenant_users tu
            join public.users u
              on u.id = tu.user_id
            where tu.tenant_id = cast(:tenant_id as varchar)
              and u.id = cast(:user_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _get_credentials_state(session: AsyncSession, user_id: str) -> dict | None:
    result = await session.execute(
        text(
            """
            select
                password_hash,
                is_password_set,
                failed_login_attempts,
                refresh_token_version,
                locked_until,
                last_login_at,
                last_failed_login_at
            from public.user_credentials
            where user_id = cast(:user_id as varchar)
            """
        ),
        {"user_id": user_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _get_role_names(session: AsyncSession, tenant_id: str, user_id: str) -> list[str]:
    result = await session.execute(
        text(
            """
            select r.name
            from public.tenant_user_roles tur
            join public.roles r
              on r.id = tur.role_id
             and r.tenant_id = tur.tenant_id
            where tur.tenant_id = cast(:tenant_id as varchar)
              and tur.user_id = cast(:user_id as varchar)
            order by r.name
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    return [str(row.name) for row in result]


async def _get_refresh_token_record(session: AsyncSession, token_id: str) -> dict | None:
    result = await session.execute(
        text(
            """
            select
                id,
                user_id,
                tenant_id,
                token_hash,
                family_id,
                expires_at,
                last_used_at,
                revoked_at,
                rotated_at,
                replaced_by_token_id,
                revoked_reason
            from public.auth_refresh_tokens
            where id = cast(:token_id as varchar)
            """
        ),
        {"token_id": token_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _get_password_reset_record(session: AsyncSession, token_id: str) -> dict | None:
    result = await session.execute(
        text(
            """
            select
                id,
                user_id,
                tenant_id,
                token_hash,
                expires_at,
                used_at
            from public.password_reset_tokens
            where id = cast(:token_id as varchar)
            """
        ),
        {"token_id": token_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _write_audit_log(
    *,
    tenant_id: str,
    action: str,
    actor_user_id: str | None = None,
    actor_ip: str | None = None,
    request_id: str | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    status_code: int | HTTPStatus | None = None,
    message: str | None = None,
    meta: dict | None = None,
) -> None:
    async with async_session_factory() as session:
        try:
            await set_tenant_guc(session, tenant_id)
            await session.execute(
                text(
                    """
                    insert into public.audit_logs (
                        id,
                        tenant_id,
                        actor_user_id,
                        actor_ip,
                        request_id,
                        action,
                        resource,
                        resource_id,
                        status_code,
                        message,
                        metadata
                    )
                    values (
                        cast(:id as varchar),
                        cast(:tenant_id as varchar),
                        cast(:actor_user_id as varchar),
                        cast(:actor_ip as varchar),
                        cast(:request_id as varchar),
                        cast(:action as varchar),
                        cast(:resource as varchar),
                        cast(:resource_id as varchar),
                        :status_code,
                        :message,
                        cast(:meta as jsonb)
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "actor_user_id": actor_user_id,
                    "actor_ip": actor_ip,
                    "request_id": request_id,
                    "action": action,
                    "resource": resource,
                    "resource_id": resource_id,
                    "status_code": int(status_code) if status_code is not None else None,
                    "message": message,
                    "meta": meta,
                },
            )
            await session.commit()
        except Exception:
            await session.rollback()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
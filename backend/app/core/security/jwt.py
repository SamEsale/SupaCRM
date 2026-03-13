from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from app.core.config import settings


class TokenValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime


def create_access_token(*, subject: str, tenant_id: str, roles: list[str] | None = None) -> str:
    return issue_access_token(subject=subject, tenant_id=tenant_id, roles=roles).token


def issue_access_token(
    *,
    subject: str,
    tenant_id: str,
    roles: list[str] | None = None,
) -> IssuedToken:
    return _issue_token(
        subject=subject,
        tenant_id=tenant_id,
        token_type="access",
        ttl=timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES),
        secret=settings.JWT_SECRET,
        extra_claims={"roles": roles or []},
    )


def issue_refresh_token(
    *,
    subject: str,
    tenant_id: str,
    family_id: str,
    token_version: int,
) -> IssuedToken:
    return _issue_token(
        subject=subject,
        tenant_id=tenant_id,
        token_type="refresh",
        ttl=timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
        secret=settings.REFRESH_TOKEN_SECRET,
        extra_claims={"family_id": family_id, "token_version": token_version},
    )


def issue_password_reset_token(
    *,
    subject: str,
    tenant_id: str,
) -> IssuedToken:
    secret = settings.PASSWORD_RESET_TOKEN_SECRET or settings.JWT_SECRET
    return _issue_token(
        subject=subject,
        tenant_id=tenant_id,
        token_type="password_reset",
        ttl=timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
        secret=secret,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    return _decode_token(
        token=token,
        secret=settings.JWT_SECRET,
        expected_type="access",
        required_claims=("sub", "tenant_id", "jti", "exp", "iat", "iss", "aud", "typ"),
    )


def decode_refresh_token(token: str) -> Dict[str, Any]:
    return _decode_token(
        token=token,
        secret=settings.REFRESH_TOKEN_SECRET,
        expected_type="refresh",
        required_claims=(
            "sub",
            "tenant_id",
            "jti",
            "family_id",
            "token_version",
            "exp",
            "iat",
            "iss",
            "aud",
            "typ",
        ),
    )


def decode_password_reset_token(token: str) -> Dict[str, Any]:
    secret = settings.PASSWORD_RESET_TOKEN_SECRET or settings.JWT_SECRET
    return _decode_token(
        token=token,
        secret=secret,
        expected_type="password_reset",
        required_claims=("sub", "tenant_id", "jti", "exp", "iat", "iss", "aud", "typ"),
    )


def _issue_token(
    *,
    subject: str,
    tenant_id: str,
    token_type: str,
    ttl: timedelta,
    secret: str,
    extra_claims: Dict[str, Any] | None = None,
) -> IssuedToken:
    now = datetime.now(timezone.utc)
    expires_at = now + ttl
    jti = str(uuid.uuid4())
    payload: Dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "jti": jti,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)
    return IssuedToken(token=token, jti=jti, expires_at=expires_at)


def _decode_token(
    *,
    token: str,
    secret: str,
    expected_type: str,
    required_claims: tuple[str, ...],
) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"require": list(required_claims)},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenValidationError(f"{expected_type} token expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenValidationError(f"invalid {expected_type} token") from exc

    if payload.get("typ") != expected_type:
        raise TokenValidationError(f"invalid {expected_type} token type")
    return payload

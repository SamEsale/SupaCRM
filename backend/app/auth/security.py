from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db

# If you already have password hashing utilities, keep using them from core/utils.
# This file focuses on token parsing + user loading + request.state wiring.

bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, subject: str, tenant_id: str, roles: Optional[list[str]] = None) -> str:
    """
    Creates a short-lived JWT access token.

    subject: user id (string)
    tenant_id: tenant UUID (string)
    roles: list of role names (optional; prefer server-side RBAC checks in DB)
    """
    ttl_minutes = getattr(settings, "ACCESS_TOKEN_TTL_MINUTES", 15)
    payload: Dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "roles": roles or [],
        "type": "access",
        "iat": int(_utcnow().timestamp()),
        "exp": int((_utcnow() + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(*, subject: str, tenant_id: str, token_version: int = 0) -> str:
    """
    Creates a long-lived refresh token. Recommended: rotate and version refresh tokens server-side.

    token_version can be stored on the user record; increment to revoke existing refresh tokens.
    """
    ttl_days = getattr(settings, "REFRESH_TOKEN_TTL_DAYS", 30)
    payload: Dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "token_version": token_version,
        "type": "refresh",
        "iat": int(_utcnow().timestamp()),
        "exp": int((_utcnow() + timedelta(days=ttl_days)).timestamp()),
    }
    return jwt.encode(payload, settings.REFRESH_TOKEN_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise AuthError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.PyJWTError:
        raise AuthError("Invalid token")


def decode_refresh_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.REFRESH_TOKEN_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise AuthError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Refresh token expired")
    except jwt.PyJWTError:
        raise AuthError("Invalid refresh token")


def get_token_from_request(credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    if credentials is None or not credentials.credentials:
        raise AuthError("Missing bearer token")
    return credentials.credentials


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """
    Returns a dict principal:
      {
        "user_id": UUID,
        "tenant_id": UUID,
        "roles": [str],
      }

    Also sets request.state.user so middleware/auditing can reference it.
    """
    token = get_token_from_request(credentials)
    payload = decode_access_token(token)

    try:
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
    except Exception:
        raise AuthError("Invalid token claims")

    roles = payload.get("roles") or []

    principal = {"user_id": user_id, "tenant_id": tenant_id, "roles": roles}

    # Expose to request.state for audit context middleware
    request.state.user = {"id": user_id, "tenant_id": tenant_id, "roles": roles}

    return principal


def require_roles(*required_roles: str):
    """
    Simple role gate. Prefer permission-based gates for fine-grained control.
    """

    def _dep(principal: Dict[str, Any] = Depends(get_current_principal)) -> Dict[str, Any]:
        roles = set(principal.get("roles") or [])
        if not roles.intersection(set(required_roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return principal

    return _dep

"""Authentication and JWT token utilities."""
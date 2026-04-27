from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import main as main_module
from app.auth import routes as auth_routes
from app.auth import service as auth_service
from app.auth.service import CurrentUserProfile, TokenPairResult, login_user
from app.core.security import deps as auth_deps
from app.core.security.jwt import decode_access_token, issue_access_token, issue_refresh_token
from app.db_deps import get_auth_db


class _FakeResult:
    def __init__(self, rows: list[dict[str, object]] | None) -> None:
        self._rows = rows or []

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows

    def first(self) -> dict[str, object] | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, rows: object | None) -> None:
        if rows is None:
            self.rows: list[dict[str, object]] = []
        elif isinstance(rows, dict):
            self.rows = [rows]
        else:
            self.rows = list(rows)  # type: ignore[arg-type]

    async def execute(self, statement, params: dict[str, object] | None = None) -> _FakeResult:
        return _FakeResult(self.rows)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def close(self) -> None:
        return None


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_login_response_token_claim_and_tenant_id_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop(*_: object, **__: object) -> None:
        return None

    async def _fake_tenant_state(*_: object, **__: object) -> dict[str, object]:
        return {"id": "supacrm-test", "status": "active", "is_active": True}

    async def _fake_identity(*_: object, **__: object) -> dict[str, object]:
        return {
            "user_id": "user-1",
            "email": "supacrm@test.com",
            "full_name": "SupaCRM",
            "user_is_active": True,
            "membership_is_active": True,
            "is_owner": True,
        }

    async def _fake_credentials(*_: object, **__: object) -> dict[str, object]:
        return {
            "password_hash": "hash",
            "is_password_set": True,
            "failed_login_attempts": 0,
            "refresh_token_version": 1,
            "locked_until": None,
        }

    async def _fake_roles(*_: object, **__: object) -> list[str]:
        return ["owner", "admin"]

    async def _fake_issue_token_pair(*_: object, **kwargs: object) -> TokenPairResult:
        access_token = issue_access_token(
            subject=str(kwargs["user_id"]),
            tenant_id=str(kwargs["tenant_id"]),
            roles=list(kwargs["roles"]),
        )
        refresh_token = issue_refresh_token(
            subject=str(kwargs["user_id"]),
            tenant_id=str(kwargs["tenant_id"]),
            family_id="family-1",
            token_version=int(kwargs["token_version"]),
        )
        return TokenPairResult(
            access_token=access_token.token,
            refresh_token=refresh_token.token,
            tenant_id=str(kwargs["tenant_id"]),
            access_token_expires_at=access_token.expires_at,
            refresh_token_expires_at=refresh_token.expires_at,
            access_token_jti=access_token.jti,
            refresh_token_jti=refresh_token.jti,
        )

    monkeypatch.setattr(auth_service.settings, "ENV", "dev")
    monkeypatch.setattr(auth_service, "admin_session_factory", lambda: _FakeSessionContext(_FakeSession([{"tenant_id": "supacrm-test"}])))
    monkeypatch.setattr(auth_service, "async_session_factory", lambda: _FakeSessionContext(_FakeSession([{"tenant_status": "active", "tenant_is_active": True, "user_is_active": True, "membership_is_active": True}])))
    monkeypatch.setattr(auth_service, "set_tenant_guc", _noop)
    monkeypatch.setattr(auth_service, "_get_tenant_state", _fake_tenant_state)
    monkeypatch.setattr(auth_service, "_get_identity_by_email", _fake_identity)
    monkeypatch.setattr(auth_service, "_get_credentials_state", _fake_credentials)
    monkeypatch.setattr(auth_service, "verify_password", lambda *_: True)
    monkeypatch.setattr(auth_service, "_get_role_names", _fake_roles)
    monkeypatch.setattr(auth_service, "_issue_token_pair", _fake_issue_token_pair)
    monkeypatch.setattr(auth_service, "_reset_login_state", _noop)
    monkeypatch.setattr(auth_service, "_warm_auth_cache", _noop)
    monkeypatch.setattr(auth_service, "_write_audit_log", _noop)

    result = await login_user(
        tenant_id=None,
        email="supacrm@test.com",
        password="AdminTest123!",
    )
    decoded = decode_access_token(result.access_token)

    assert result.tenant_id == "supacrm-test"
    assert decoded["tenant_id"] == "supacrm-test"
    assert decoded["sub"] == "user-1"
    assert decoded["tenant_id"] == result.tenant_id


def test_protected_route_requires_tenant_header(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_init_db() -> None:
        return None

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)

    with TestClient(main_module.app) as client:
        response = client.get("/crm/companies", headers={"Authorization": "Bearer token"})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Missing required tenant header: X-Tenant-Id"


def test_protected_route_rejects_tenant_header_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_init_db() -> None:
        return None

    async def _override_principal() -> dict[str, object]:
        return {"sub": "user-1", "tenant_id": "tenant-a", "roles": ["admin"]}

    async def _override_auth_db():
        yield object()

    async def _fake_current_profile(*_: object, **__: object) -> CurrentUserProfile:
        return CurrentUserProfile(
            user_id="user-1",
            tenant_id="tenant-a",
            email="supacrm@test.com",
            full_name="SupaCRM",
            roles=["admin"],
            is_owner=True,
            user_is_active=True,
            membership_is_active=True,
            tenant_is_active=True,
        )

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(auth_routes, "get_current_user_profile", _fake_current_profile)
    main_module.app.dependency_overrides[auth_routes.get_current_principal] = _override_principal
    main_module.app.dependency_overrides[get_auth_db] = _override_auth_db

    try:
        with TestClient(main_module.app) as client:
            response = client.get(
                "/auth/whoami",
                headers={
                    "Authorization": "Bearer token",
                    "X-Tenant-Id": "tenant-b",
                },
            )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Tenant mismatch (header tenant does not match token tenant)"


def test_whoami_uses_the_authenticated_tenant_context(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_init_db() -> None:
        return None

    captured: dict[str, str] = {}

    async def _override_principal() -> dict[str, object]:
        return {"sub": "user-1", "tenant_id": "tenant-a", "roles": ["admin"]}

    async def _override_auth_db():
        yield object()

    async def _fake_current_profile(
        *,
        db: object,
        tenant_id: str,
        user_id: str,
    ) -> CurrentUserProfile:
        captured["tenant_id"] = tenant_id
        captured["user_id"] = user_id
        return CurrentUserProfile(
            user_id=user_id,
            tenant_id=tenant_id,
            email="supacrm@test.com",
            full_name="SupaCRM",
            roles=["admin"],
            is_owner=True,
            user_is_active=True,
            membership_is_active=True,
            tenant_is_active=True,
        )

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(auth_routes, "get_current_user_profile", _fake_current_profile)
    main_module.app.dependency_overrides[auth_routes.get_current_principal] = _override_principal
    main_module.app.dependency_overrides[get_auth_db] = _override_auth_db

    try:
        with TestClient(main_module.app) as client:
            response = client.get(
                "/auth/whoami",
                headers={
                    "Authorization": "Bearer token",
                    "X-Tenant-Id": "tenant-a",
                },
            )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-a"
    assert captured == {"tenant_id": "tenant-a", "user_id": "user-1"}


@pytest.mark.asyncio
async def test_get_current_principal_rejects_inactive_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = issue_access_token(subject="user-1", tenant_id="tenant-a", roles=["admin"])
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/crm/companies",
            "raw_path": b"/crm/companies",
            "query_string": b"",
            "headers": [(b"x-tenant-id", b"tenant-a")],
            "client": ("testclient", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "root_path": "",
            "app": object(),
            "state": {},
        }
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token.token)

    class _AsyncSessionContext:
        async def __aenter__(self) -> _FakeSession:
            return _FakeSession(
                {
                    "tenant_status": "active",
                    "tenant_is_active": True,
                    "user_is_active": True,
                    "membership_is_active": False,
                }
            )

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    async def _noop(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(auth_deps, "async_session_factory", lambda: _AsyncSessionContext())
    monkeypatch.setattr(auth_deps, "set_tenant_guc", _noop)

    async def _no_snapshot(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(auth_deps.auth_cache, "get_principal_snapshot", _no_snapshot)

    with pytest.raises(HTTPException) as exc_info:
        await auth_deps.get_current_principal(request, creds=credentials)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authenticated account is inactive"

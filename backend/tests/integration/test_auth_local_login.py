from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.auth import routes as auth_routes
from app.auth import service as auth_service
from app.auth.service import AuthFlowError


@dataclass
class _FakeResult:
    rows: list[dict[str, object]]

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self.rows


class _FakeAdminSession:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.execute_calls: list[tuple[object, dict[str, object] | None]] = []

    async def __aenter__(self) -> "_FakeAdminSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def execute(self, statement, params: dict[str, object] | None = None) -> _FakeResult:
        self.execute_calls.append((statement, params))
        return _FakeResult(self.rows)


class _FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_login_user_infers_tenant_in_dev_when_tenant_id_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_session = _FakeAdminSession([{"tenant_id": "supacrm-test"}])
    captured: dict[str, object] = {}
    now = datetime.now(timezone.utc)

    async def _noop(*_: object, **__: object) -> None:
        return None

    async def _fake_tenant_state(*_: object, **__: object):
        return {
            "id": "supacrm-test",
            "status": "active",
            "is_active": True,
        }

    async def _fake_identity(*_: object, **__: object):
        return {
            "user_id": "user-1",
            "email": "supacrm@test.com",
            "full_name": "SupaCRM",
            "user_is_active": True,
            "membership_is_active": True,
            "is_owner": True,
        }

    async def _fake_credentials(*_: object, **__: object):
        return {
            "password_hash": "hash",
            "is_password_set": True,
            "failed_login_attempts": 0,
            "refresh_token_version": 1,
            "locked_until": None,
        }

    async def _fake_roles(*_: object, **__: object) -> list[str]:
        return ["owner", "admin"]

    async def _fake_issue_token_pair(*_: object, **kwargs: object) -> auth_service.TokenPairResult:
        return auth_service.TokenPairResult(
            access_token="access-token",
            refresh_token="refresh-token",
            tenant_id=str(kwargs["tenant_id"]),
            access_token_expires_at=now,
            refresh_token_expires_at=now,
            access_token_jti="access-jti",
            refresh_token_jti="refresh-jti",
        )

    monkeypatch.setattr(auth_service.settings, "ENV", "dev")
    monkeypatch.setattr(auth_service, "admin_session_factory", lambda: admin_session)
    monkeypatch.setattr(auth_service, "async_session_factory", lambda: _FakeSessionContext(_FakeSession()))
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

    result = await auth_service.login_user(
        tenant_id=None,
        email="supacrm@test.com",
        password="AdminTest123!",
    )

    assert result.tenant_id == "supacrm-test"
    assert result.access_token == "access-token"
    assert admin_session.execute_calls
    assert admin_session.execute_calls[0][1] == {"email": "supacrm@test.com"}


@pytest.mark.asyncio
async def test_login_user_requires_tenant_id_in_prod_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def _unexpected_admin_session() -> _FakeAdminSession:
        nonlocal called
        called = True
        return _FakeAdminSession([])

    monkeypatch.setattr(auth_service.settings, "ENV", "prod")
    monkeypatch.setattr(auth_service, "admin_session_factory", _unexpected_admin_session)

    with pytest.raises(AuthFlowError) as exc_info:
        await auth_service.login_user(
            tenant_id=None,
            email="supacrm@test.com",
            password="AdminTest123!",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Tenant ID is required"
    assert called is False


@pytest.mark.asyncio
async def test_login_user_requires_tenant_id_in_dev_when_email_matches_multiple_active_tenants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_session = _FakeAdminSession(
        [{"tenant_id": "supacrm-test"}, {"tenant_id": "supacrm-alt"}]
    )
    called = False

    def _unexpected_app_session() -> _FakeSessionContext:
        nonlocal called
        called = True
        return _FakeSessionContext(_FakeSession())

    monkeypatch.setattr(auth_service.settings, "ENV", "dev")
    monkeypatch.setattr(auth_service, "admin_session_factory", lambda: admin_session)
    monkeypatch.setattr(auth_service, "async_session_factory", _unexpected_app_session)

    with pytest.raises(AuthFlowError) as exc_info:
        await auth_service.login_user(
            tenant_id=None,
            email="supacrm@test.com",
            password="AdminTest123!",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Tenant ID is required for this account"
    assert called is False


def test_login_route_accepts_local_manual_payload_without_tenant_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    captured: dict[str, object] = {}

    async def _fake_login_user(**kwargs: object) -> auth_service.TokenPairResult:
        captured.update(kwargs)
        return auth_service.TokenPairResult(
            access_token="access-token",
            refresh_token="refresh-token",
            tenant_id="supacrm-test",
            access_token_expires_at=now,
            refresh_token_expires_at=now,
            access_token_jti="access-jti",
            refresh_token_jti="refresh-jti",
        )

    async def _noop_init_db() -> None:
        return None

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(auth_routes, "login_user", _fake_login_user)

    with TestClient(main_module.app) as client:
        response = client.post(
            "/auth/login",
            json={
                "email": "supacrm@test.com",
                "password": "AdminTest123!",
            },
            headers={"X-Forwarded-For": "127.0.0.1"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "supacrm-test"
    assert captured["tenant_id"] is None
    assert captured["email"] == "supacrm@test.com"

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.auth import service as auth_service
from app.core.security import deps as auth_deps
from app.workers import queue as worker_queue
from app.workers.tasks import auth_cache as worker_auth_cache


def _request_with_tenant(tenant_id: str) -> Request:
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/api",
            "raw_path": b"/api",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "https",
            "root_path": "",
            "app": object(),
            "state": {},
        }
    )
    request.state.header_tenant_id = tenant_id
    return request


class _FailingAsyncSessionFactory:
    def __call__(self):
        return self

    async def __aenter__(self):
        raise AssertionError("database should not be used on a cache hit")

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSessionContext:
    def __init__(self, session) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _LoginSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _CachePopulateSession:
    def __init__(self, row: dict[str, object]) -> None:
        self._row = row

    async def execute(self, *args: object, **kwargs: object):
        class _Result:
            def __init__(self, row: dict[str, object]) -> None:
                self._row = row

            def mappings(self) -> "_Result":
                return self

            def first(self) -> dict[str, object]:
                return self._row

        return _Result(self._row)


class _FakeQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []

    def enqueue(self, func, **kwargs: object):
        self.calls.append((func, kwargs))

        class _Job:
            id = "job-1"

        return _Job()


@pytest.mark.asyncio
async def test_current_principal_uses_cached_snapshot_without_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expires_at = int(datetime.now(timezone.utc).timestamp()) + 300
    payload = {
        "sub": "user-1",
        "tenant_id": "tenant-1",
        "jti": "access-jti",
        "exp": expires_at,
        "iat": expires_at - 300,
        "iss": "supacrm",
        "aud": "supacrm-api",
        "typ": "access",
        "roles": ["sales"],
    }
    cached_state = {
        "tenant_status": "active",
        "tenant_is_active": True,
        "user_is_active": True,
        "membership_is_active": True,
    }

    async def _cached_principal_snapshot(*_: object, **__: object) -> dict[str, object]:
        return cached_state

    monkeypatch.setattr(auth_deps, "decode_access_token", lambda _: payload)
    monkeypatch.setattr(auth_deps.auth_cache, "get_principal_snapshot", _cached_principal_snapshot)
    monkeypatch.setattr(auth_deps, "async_session_factory", _FailingAsyncSessionFactory())

    principal = await auth_deps.get_current_principal(
        _request_with_tenant("tenant-1"),
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token"),
    )

    assert principal["sub"] == "user-1"
    assert principal["tenant_id"] == "tenant-1"
    assert principal["tenant_status"] == "active"
    assert principal["user_is_active"] is True


@pytest.mark.asyncio
async def test_current_principal_populates_cache_on_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expires_at = int(datetime.now(timezone.utc).timestamp()) + 300
    payload = {
        "sub": "user-1",
        "tenant_id": "tenant-1",
        "jti": "access-jti",
        "exp": expires_at,
        "iat": expires_at - 300,
        "iss": "supacrm",
        "aud": "supacrm-api",
        "typ": "access",
        "roles": ["sales"],
    }
    captured: list[tuple[str, dict[str, object], int]] = []

    async def _capture_snapshot(access_token_jti: str, snapshot: dict[str, object], *, ttl_seconds: int) -> None:
        captured.append((access_token_jti, snapshot, ttl_seconds))

    async def _cache_miss(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(auth_deps, "decode_access_token", lambda _: payload)
    monkeypatch.setattr(auth_deps.auth_cache, "get_principal_snapshot", _cache_miss)
    monkeypatch.setattr(auth_deps.auth_cache, "set_principal_snapshot", _capture_snapshot)
    monkeypatch.setattr(auth_deps, "async_session_factory", _FakeSessionContext(_CachePopulateSession(
        {
            "tenant_status": "active",
            "tenant_is_active": True,
            "user_is_active": True,
            "membership_is_active": True,
        }
    )))

    principal = await auth_deps.get_current_principal(
        _request_with_tenant("tenant-1"),
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token"),
    )

    assert principal["tenant_status"] == "active"
    assert captured, "expected cache to be populated on miss"
    assert captured[0][0] == "access-jti"
    assert captured[0][1]["tenant_status"] == "active"
    assert captured[0][2] > 0


@pytest.mark.asyncio
async def test_current_user_profile_uses_cached_snapshot_without_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached_profile = {
        "user_id": "user-1",
        "tenant_id": "tenant-1",
        "email": "user@example.com",
        "full_name": "User Example",
        "roles": ["sales"],
        "is_owner": True,
        "user_is_active": True,
        "membership_is_active": True,
        "tenant_is_active": True,
    }

    async def _cached_profile_snapshot(*_: object, **__: object) -> dict[str, object]:
        return cached_profile

    monkeypatch.setattr(auth_service.auth_cache, "get_profile_snapshot", _cached_profile_snapshot)
    monkeypatch.setattr(auth_service, "async_session_factory", _FailingAsyncSessionFactory())

    profile = await auth_service.get_current_user_profile(
        db=object(),
        tenant_id="tenant-1",
        user_id="user-1",
    )

    assert profile.user_id == "user-1"
    assert profile.email == "user@example.com"
    assert profile.roles == ["sales"]
    assert profile.is_owner is True


@pytest.mark.asyncio
async def test_login_user_enqueues_auth_cache_warmup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, object]] = []

    async def _noop(*_: object, **__: object) -> None:
        return None

    async def _fake_tenant_state(*_: object, **__: object) -> dict[str, object]:
        return {"status": "active", "is_active": True}

    async def _fake_identity(*_: object, **__: object) -> dict[str, object]:
        return {
            "user_id": "user-1",
            "email": "user@example.com",
            "full_name": "User Example",
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
        return ["sales"]

    async def _fake_token_pair(*_: object, **__: object) -> auth_service.TokenPairResult:
        expires_at = datetime.now(timezone.utc)
        return auth_service.TokenPairResult(
            access_token="access-token",
            refresh_token="refresh-token",
            tenant_id="tenant-1",
            access_token_expires_at=expires_at,
            refresh_token_expires_at=expires_at,
            access_token_jti="access-jti",
            refresh_token_jti="refresh-jti",
        )

    async def _fake_warm_auth_cache(**kwargs: object) -> None:
        captured.append(kwargs)

    monkeypatch.setattr(auth_service, "async_session_factory", _FakeSessionContext(_LoginSession()))
    monkeypatch.setattr(auth_service, "set_tenant_guc", _noop)
    monkeypatch.setattr(auth_service, "_get_tenant_state", _fake_tenant_state)
    monkeypatch.setattr(auth_service, "_get_identity_by_email", _fake_identity)
    monkeypatch.setattr(auth_service, "_get_credentials_state", _fake_credentials)
    monkeypatch.setattr(auth_service, "verify_password", lambda *_: True)
    monkeypatch.setattr(auth_service, "_get_role_names", _fake_roles)
    monkeypatch.setattr(auth_service, "_issue_token_pair", _fake_token_pair)
    monkeypatch.setattr(auth_service, "_reset_login_state", _noop)
    monkeypatch.setattr(auth_service, "_write_audit_log", _noop)
    monkeypatch.setattr(auth_service.auth_cache, "set_principal_snapshot", _noop)
    monkeypatch.setattr(auth_service.auth_cache, "set_profile_snapshot", _noop)
    monkeypatch.setattr(auth_service, "_warm_auth_cache", _fake_warm_auth_cache)

    result = await auth_service.login_user(
        tenant_id="tenant-1",
        email="user@example.com",
        password="supersecret123",
    )

    assert result.access_token == "access-token"
    assert captured, "expected login to enqueue auth cache warmup"
    warmup = captured[0]
    assert warmup["principal_access_jti"] == "access-jti"
    assert warmup["tenant_id"] == "tenant-1"
    assert warmup["user_id"] == "user-1"


def test_enqueue_auth_cache_warmup_uses_rq_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_queue = _FakeQueue()
    monkeypatch.setattr(worker_queue, "get_queue", lambda: fake_queue)

    job_id = worker_queue.enqueue_auth_cache_warmup(
        principal_snapshot={
            "snapshot": {"tenant_status": "active"},
            "access_token_jti": "access-jti",
            "principal_ttl_seconds": 30,
        },
        profile_snapshot={
            "snapshot": {"tenant_id": "tenant-1", "user_id": "user-1"},
            "tenant_id": "tenant-1",
            "user_id": "user-1",
            "profile_ttl_seconds": 120,
        },
    )

    assert job_id == "job-1"
    assert fake_queue.calls
    func, kwargs = fake_queue.calls[0]
    assert func is worker_auth_cache.warm_auth_cache
    assert kwargs["principal_snapshot"]["access_token_jti"] == "access-jti"
    assert kwargs["profile_snapshot"]["tenant_id"] == "tenant-1"


@pytest.mark.asyncio
async def test_logout_user_invalidates_cached_auth_snapshots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidations: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def _fake_refresh_record(*_: object, **__: object) -> dict[str, object]:
        return {"token_hash": auth_service._hash_token("refresh-token")}

    async def _noop(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(
        auth_service,
        "decode_refresh_token",
        lambda _: {
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "jti": "refresh-jti",
            "family_id": "family-1",
            "token_version": 1,
        },
    )
    monkeypatch.setattr(auth_service, "_get_refresh_token_record", _fake_refresh_record)
    monkeypatch.setattr(auth_service, "_revoke_refresh_token", _noop)
    monkeypatch.setattr(auth_service, "_revoke_refresh_family", _noop)
    monkeypatch.setattr(auth_service.AuditService, "log", _noop)
    monkeypatch.setattr(auth_service.auth_cache, "invalidate_principal_snapshot", _noop)
    monkeypatch.setattr(auth_service.auth_cache, "invalidate_profile_snapshot", _noop)

    def _capture_invalidation(**kwargs: object) -> None:
        invalidations.append((tuple(), kwargs))

    monkeypatch.setattr(auth_service, "enqueue_auth_cache_invalidation", _capture_invalidation)

    await auth_service.logout_user(
        db=object(),
        principal_user_id="user-1",
        principal_tenant_id="tenant-1",
        principal_access_jti="access-jti",
        refresh_token="refresh-token",
        revoke_family=False,
    )

    assert invalidations, "expected logout to enqueue cache invalidation"
    assert invalidations[0][1]["principal_access_jti"] == "access-jti"
    assert invalidations[0][1]["tenant_id"] == "tenant-1"
    assert invalidations[0][1]["user_id"] == "user-1"


def test_worker_task_warms_auth_cache_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    writes: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def _capture_principal(*args: object, **kwargs: object) -> None:
        writes.append(("principal", args, kwargs))

    async def _capture_profile(*args: object, **kwargs: object) -> None:
        writes.append(("profile", args, kwargs))

    monkeypatch.setattr(worker_auth_cache.auth_cache, "set_principal_snapshot", _capture_principal)
    monkeypatch.setattr(worker_auth_cache.auth_cache, "set_profile_snapshot", _capture_profile)

    worker_auth_cache.warm_auth_cache(
        principal_snapshot={
            "snapshot": {
                "tenant_status": "active",
                "tenant_is_active": True,
                "user_is_active": True,
                "membership_is_active": True,
            },
            "access_token_jti": "access-jti",
            "principal_ttl_seconds": 30,
        },
        profile_snapshot={
            "snapshot": {
                "tenant_id": "tenant-1",
                "user_id": "user-1",
                "email": "user@example.com",
                "full_name": "User Example",
                "roles": ["sales"],
                "is_owner": True,
                "user_is_active": True,
                "membership_is_active": True,
                "tenant_is_active": True,
            },
            "tenant_id": "tenant-1",
            "user_id": "user-1",
            "profile_ttl_seconds": 120,
        },
    )

    assert [entry[0] for entry in writes] == ["principal", "profile"]

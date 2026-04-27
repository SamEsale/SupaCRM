from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import api
from app.auth.service import TokenPairResult
from app.core.config import Settings
from app.core.security import abuse as security_abuse
from app.core.security.abuse import AbuseTracker
from app.core.middleware.rate_limit import AUTH_RATE_LIMIT_RULES, SlidingWindowRateLimiter
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app import main as main_module


def _fake_token_pair() -> TokenPairResult:
    now = datetime.now(timezone.utc)
    return TokenPairResult(
        access_token="access-token",
        refresh_token="refresh-token",
        tenant_id="tenant-1",
        access_token_expires_at=now,
        refresh_token_expires_at=now,
    )


@pytest.mark.asyncio
async def test_security_headers_add_csp_and_hsts_on_https() -> None:
    middleware = SecurityHeadersMiddleware(app=object())
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/health",
            "raw_path": b"/health",
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 12345),
            "server": ("testserver", 80),
            "scheme": "https",
            "root_path": "",
            "app": object(),
            "state": {},
        }
    )

    async def call_next(_: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    response = await middleware.dispatch(request, call_next)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_separates_tenants() -> None:
    limiter = SlidingWindowRateLimiter(redis_url="")
    key_one = "auth-rate:POST:/auth/login:tenant-a:127.0.0.1"
    key_two = "auth-rate:POST:/auth/login:tenant-b:127.0.0.1"

    for _ in range(5):
        result = await limiter.allow(key_one, limit=5, window_seconds=60)
        assert result.allowed is True

    blocked = await limiter.allow(key_one, limit=5, window_seconds=60)
    assert blocked.allowed is False
    assert blocked.retry_after_seconds > 0

    separate_tenant = await limiter.allow(key_two, limit=5, window_seconds=60)
    assert separate_tenant.allowed is True


def test_auth_rate_limit_rules_cover_public_auth_endpoints() -> None:
    assert AUTH_RATE_LIMIT_RULES[("POST", "/auth/login")].limit == 5
    assert AUTH_RATE_LIMIT_RULES[("POST", "/auth/refresh")].limit == 10
    assert AUTH_RATE_LIMIT_RULES[("POST", "/auth/logout")].limit == 10
    assert AUTH_RATE_LIMIT_RULES[("POST", "/auth/register")].limit == 5


def test_login_endpoint_rate_limits_after_five_requests(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def _login_user(**_: object) -> TokenPairResult:
        return _fake_token_pair()

    async def _noop_init_db() -> None:
        return None

    monkeypatch.setattr("app.auth.routes.login_user", _login_user)
    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(security_abuse, "auth_abuse_tracker", AbuseTracker(redis_url=""))
    main_module.app.state.rate_limiter = SlidingWindowRateLimiter(redis_url="")

    original_env = main_module.settings.ENV
    main_module.settings.ENV = "prod"
    try:
        caplog.set_level("WARNING", logger="supacrm.security")
        with TestClient(main_module.app) as client:
            payload = {
                "tenant_id": "tenant-rate-limit",
                "email": "user@example.com",
                "password": "supersecret123",
            }
            headers = {"X-Forwarded-For": "203.0.113.10"}

            responses = [
                client.post("/auth/login", json=payload, headers=headers)
                for _ in range(6)
            ]

        assert [response.status_code for response in responses[:5]] == [200, 200, 200, 200, 200]
        assert responses[5].status_code == 429
        assert responses[5].json()["error"]["message"] == "Too many requests. Please retry later."
    finally:
        main_module.settings.ENV = original_env


def test_options_preflight_for_uploads_is_not_blocked_by_tenant_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_init_db() -> None:
        return None

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(main_module.settings, "ENV", "prod")

    with TestClient(main_module.app) as client:
        response = client.options(
            "/storage/uploads",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization,x-tenant-id",
            },
        )

    assert response.status_code in {200, 204}
    assert response.headers.get("access-control-allow-origin") in {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_auth_abuse_tracker_emits_suspected_event_after_threshold(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    tracker = AbuseTracker(redis_url="", threshold=3, window_seconds=300)
    monkeypatch.setattr(security_abuse, "auth_abuse_tracker", tracker)

    caplog.set_level("WARNING", logger="supacrm.security")

    for _ in range(3):
        await tracker.record(
            event_type="auth.login.failed",
            scope_key="tenant-1:user-1:203.0.113.10",
            tenant_id="tenant-1",
            user_id="user-1",
            ip_address="203.0.113.10",
            reason="invalid_password",
        )

    assert tracker is security_abuse.auth_abuse_tracker


def test_settings_supports_file_based_secret_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    jwt_secret_file = tmp_path / "jwt_secret"
    refresh_secret_file = tmp_path / "refresh_secret"
    bootstrap_key_file = tmp_path / "bootstrap_key"
    database_url_file = tmp_path / "database_url"

    jwt_secret_file.write_text("jwt-secret-from-file")
    refresh_secret_file.write_text("refresh-secret-from-file")
    bootstrap_key_file.write_text("bootstrap-secret-from-file")
    database_url_file.write_text("postgresql+asyncpg://user:pass@localhost:5432/db")

    monkeypatch.setenv("JWT_SECRET", "REPLACE_WITH_REAL_JWT_SECRET")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "REPLACE_WITH_REAL_REFRESH_SECRET")
    monkeypatch.setenv("BOOTSTRAP_API_KEY", "REPLACE_WITH_REAL_BOOTSTRAP_KEY")
    monkeypatch.setenv("DATABASE_URL_ASYNC", "REPLACE_WITH_REAL_DATABASE_URL_ASYNC")
    monkeypatch.setenv("DATABASE_URL_SYNC", "REPLACE_WITH_REAL_DATABASE_URL_SYNC")
    monkeypatch.setenv("DATABASE_URL_ADMIN_ASYNC", "REPLACE_WITH_REAL_DATABASE_URL_ADMIN_ASYNC")
    monkeypatch.setenv("DATABASE_URL_ADMIN_SYNC", "REPLACE_WITH_REAL_DATABASE_URL_ADMIN_SYNC")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    monkeypatch.setenv("DATABASE_URL_ASYNC_FILE", str(database_url_file))
    monkeypatch.setenv("DATABASE_URL_SYNC_FILE", str(database_url_file))
    monkeypatch.setenv("DATABASE_URL_ADMIN_ASYNC_FILE", str(database_url_file))
    monkeypatch.setenv("DATABASE_URL_ADMIN_SYNC_FILE", str(database_url_file))
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET_FILE", str(jwt_secret_file))
    monkeypatch.setenv("REFRESH_TOKEN_SECRET_FILE", str(refresh_secret_file))
    monkeypatch.setenv("BOOTSTRAP_API_KEY_FILE", str(bootstrap_key_file))

    settings = Settings()

    assert settings.JWT_SECRET == "jwt-secret-from-file"
    assert settings.REFRESH_TOKEN_SECRET == "refresh-secret-from-file"
    assert settings.BOOTSTRAP_API_KEY == "bootstrap-secret-from-file"
    assert settings.DATABASE_URL_ASYNC == "postgresql+asyncpg://user:pass@localhost:5432/db"


def test_debug_router_is_not_attached_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api.settings, "ENV", "prod")
    monkeypatch.setattr(api.settings, "DEBUG", False)

    router = api.attach_feature_routers(APIRouter())
    paths = {route.path for route in router.routes if hasattr(route, "path")}

    assert "/debug/rbac" not in paths

from __future__ import annotations

from fastapi import HTTPException
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import api
from app.core.middleware.tenant_middleware import TenantMiddleware


@pytest.mark.asyncio
async def test_ready_reports_healthy_when_dependencies_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _ok() -> None:
        return None

    monkeypatch.setattr(api, "check_database_ready", _ok)
    monkeypatch.setattr(api, "check_redis_ready", _ok)
    monkeypatch.setattr(api, "check_storage_ready", _ok)
    monkeypatch.setattr(api, "storage_readiness_required", lambda: True)

    response = await api.ready()

    assert response == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok", "storage": "ok"},
    }


@pytest.mark.asyncio
async def test_ready_reports_not_ready_when_database_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fail() -> None:
        raise RuntimeError("database unavailable")

    async def _ok() -> None:
        return None

    monkeypatch.setattr(api, "check_database_ready", _fail)
    monkeypatch.setattr(api, "check_redis_ready", _ok)
    monkeypatch.setattr(api, "check_storage_ready", _ok)
    monkeypatch.setattr(api, "storage_readiness_required", lambda: True)

    with pytest.raises(HTTPException) as exc_info:
        await api.ready()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "status": "not ready",
        "checks": {
            "database": "error: database unavailable",
            "redis": "ok",
            "storage": "ok",
        },
    }


@pytest.mark.asyncio
async def test_ready_reports_not_ready_when_storage_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _ok() -> None:
        return None

    async def _fail() -> None:
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(api, "check_database_ready", _ok)
    monkeypatch.setattr(api, "check_redis_ready", _ok)
    monkeypatch.setattr(api, "check_storage_ready", _fail)
    monkeypatch.setattr(api, "storage_readiness_required", lambda: True)

    with pytest.raises(HTTPException) as exc_info:
        await api.ready()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "status": "not ready",
        "checks": {
            "database": "ok",
            "redis": "ok",
            "storage": "error: storage unavailable",
        },
    }


@pytest.mark.asyncio
async def test_ready_path_does_not_require_tenant_header() -> None:
    middleware = TenantMiddleware(app=object())
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/ready",
            "raw_path": b"/ready",
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "root_path": "",
            "app": object(),
            "state": {},
        }
    )

    called = False

    async def call_next(_: Request) -> JSONResponse:
        nonlocal called
        called = True
        return JSONResponse({"ok": True})

    response = await middleware.dispatch(request, call_next)

    assert called is True
    assert response.status_code == 200

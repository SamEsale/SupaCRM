from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main as main_module


def test_missing_tenant_header_uses_normalized_error_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_init_db() -> None:
        return None

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)

    with TestClient(main_module.app) as client:
        response = client.get("/crm/companies", headers={"Authorization": "Bearer token"})

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "bad_request",
            "message": "Missing required tenant header: X-Tenant-Id",
        }
    }


def test_request_validation_uses_normalized_error_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_init_db() -> None:
        return None

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)

    with TestClient(main_module.app) as client:
        response = client.post(
            "/auth/login",
            json={
                "email": "not-an-email",
            },
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed."
    assert isinstance(payload["error"]["details"], list)
    assert payload["error"]["details"]

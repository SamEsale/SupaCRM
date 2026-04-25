from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.payments.settings_service import (
    get_payment_gateway_provider_record,
    get_payment_provider_foundation,
)


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _FakeResult:
    def __init__(self, *, rows: list[dict[str, Any]] | None = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar(self) -> Any:
        return self._scalar


class FakeGatewaySettingsSession:
    def __init__(self) -> None:
        self.updated_at = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
        self.gateway_settings = {
            "default_provider": "stripe",
            "updated_at": self.updated_at.isoformat(),
            "providers": {
                "stripe": {
                    "is_enabled": True,
                    "mode": "live",
                    "publishable_key": "pk_live_tenant",
                    "secret_key": "sk_live_tenant",
                    "webhook_secret": "whsec_live_tenant",
                    "updated_at": self.updated_at.isoformat(),
                },
                "payoneer": {
                    "is_enabled": True,
                    "mode": "test",
                    "account_id": "acct_payoneer",
                    "client_id": "client_payoneer",
                    "client_secret": "secret_payoneer",
                    "webhook_secret": "whsec_payoneer",
                    "updated_at": self.updated_at.isoformat(),
                },
            },
        }

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "from information_schema.columns" in sql and "table_name = 'tenants'" in sql:
            return _FakeResult(scalar=True)

        if "select payment_gateway_settings, updated_at from public.tenants" in sql:
            if str(payload.get("tenant_id")) != "tenant-1":
                return _FakeResult(rows=[])
            return _FakeResult(
                rows=[
                    {
                        "payment_gateway_settings": self.gateway_settings,
                        "updated_at": self.updated_at,
                    }
                ]
            )

        raise AssertionError(f"Unhandled SQL in FakeGatewaySettingsSession: {sql}")


@pytest.mark.asyncio
async def test_get_payment_gateway_provider_record_includes_tenant_scoped_secrets() -> None:
    session = FakeGatewaySettingsSession()

    record = await get_payment_gateway_provider_record(
        session,
        tenant_id="tenant-1",
        provider="stripe",
    )

    assert record.provider == "stripe"
    assert record.is_enabled is True
    assert record.is_default is True
    assert record.mode == "live"
    assert record.secret_key == "sk_live_tenant"
    assert record.webhook_secret == "whsec_live_tenant"
    assert record.configuration_state == "configured"


@pytest.mark.asyncio
async def test_get_payment_provider_foundation_reports_ready_and_manual_only_states() -> None:
    session = FakeGatewaySettingsSession()

    snapshot = await get_payment_provider_foundation(session, tenant_id="tenant-1")
    providers = {provider.provider: provider for provider in snapshot.providers}

    assert snapshot.default_provider == "stripe"
    assert providers["stripe"].foundation_state == "ready"
    assert providers["stripe"].supports_automated_subscriptions is True
    assert providers["payoneer"].foundation_state == "manual_only"
    assert providers["payoneer"].supports_automated_subscriptions is False
    assert providers["revolut_business"].foundation_state == "disabled"

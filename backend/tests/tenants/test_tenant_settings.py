from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

import pytest

os.environ["DEBUG"] = "false"

from app.tenants import routes as tenant_routes
from app.tenants import service as tenant_service


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeResult:
    def __init__(self, *, rows: list[dict[str, Any]] | None = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar(self) -> Any:
        return self._scalar


class FakeTenantSettingsSession:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.row = {
            "id": "tenant-1",
            "name": "Northwind Workspace",
            "is_active": True,
            "status": "active",
            "status_reason": None,
            "legal_name": "Northwind Labs AB",
            "address_line_1": "Sveavagen 1",
            "address_line_2": None,
            "city": "Stockholm",
            "state_region": "Stockholm County",
            "postal_code": "111 57",
            "country": "Sweden",
            "vat_number": "SE123456789001",
            "default_currency": "SEK",
            "secondary_currency": "EUR",
            "secondary_currency_rate": "0.091500",
            "secondary_currency_rate_source": "operator_manual",
            "secondary_currency_rate_as_of": now,
            "logo_file_key": "tenant-logos/tenant-1/logo.png",
            "brand_primary_color": "#2563EB",
            "brand_secondary_color": "#1D4ED8",
            "sidebar_background_color": "#111827",
            "sidebar_text_color": "#FFFFFF",
            "created_at": now,
            "updated_at": now,
        }

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "from information_schema.columns" in sql and "table_name = 'tenants'" in sql:
            return _FakeResult(
                scalar=str(payload["column_name"])
                in {
                    "logo_file_key",
                    "legal_name",
                    "address_line_1",
                    "address_line_2",
                    "city",
                    "state_region",
                    "postal_code",
                    "country",
                    "vat_number",
                    "default_currency",
                    "secondary_currency",
                    "secondary_currency_rate",
                    "secondary_currency_rate_source",
                    "secondary_currency_rate_as_of",
                    "brand_primary_color",
                    "brand_secondary_color",
                    "sidebar_background_color",
                    "sidebar_text_color",
                }
            )

        if "select id, name, is_active, status, status_reason" in sql and "from public.tenants" in sql:
            return _FakeResult(rows=[dict(self.row)])

        if "update public.tenants" in sql and "returning" in sql:
            self.row.update(
                {
                    "name": payload["name"],
                    "legal_name": payload["legal_name"],
                    "address_line_1": payload["address_line_1"],
                    "address_line_2": payload["address_line_2"],
                    "city": payload["city"],
                    "state_region": payload["state_region"],
                    "postal_code": payload["postal_code"],
                    "country": payload["country"],
                    "vat_number": payload["vat_number"],
                    "default_currency": payload["default_currency"],
                    "secondary_currency": payload["secondary_currency"],
                    "secondary_currency_rate": payload["secondary_currency_rate"],
                    "secondary_currency_rate_source": payload["secondary_currency_rate_source"],
                    "secondary_currency_rate_as_of": payload["secondary_currency_rate_as_of"],
                    "brand_primary_color": payload["brand_primary_color"],
                    "brand_secondary_color": payload["brand_secondary_color"],
                    "sidebar_background_color": payload["sidebar_background_color"],
                    "sidebar_text_color": payload["sidebar_text_color"],
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            return _FakeResult(rows=[dict(self.row)])

        raise AssertionError(f"Unhandled SQL in FakeTenantSettingsSession: {sql}")


@pytest.mark.asyncio
async def test_get_tenant_details_returns_company_profile_fields() -> None:
    tenant = await tenant_service.get_tenant_details(FakeTenantSettingsSession(), tenant_id="tenant-1")

    assert tenant is not None
    assert tenant.legal_name == "Northwind Labs AB"
    assert tenant.country == "Sweden"
    assert tenant.default_currency == "SEK"
    assert tenant.secondary_currency == "EUR"
    assert str(tenant.secondary_currency_rate) == "0.091500"
    assert tenant.brand_primary_color == "#2563EB"
    assert tenant.sidebar_background_color == "#111827"


@pytest.mark.asyncio
async def test_get_current_tenant_branding_route_returns_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_get_tenant_branding(*_: object, **__: object):
        return tenant_service.TenantBrandingDetails(
            tenant_id="tenant-1",
            logo_file_key=None,
            logo_url=None,
            brand_primary_color=None,
            brand_secondary_color=None,
            sidebar_background_color=None,
            sidebar_text_color=None,
        )

    monkeypatch.setattr(tenant_routes, "get_tenant_branding", _fake_get_tenant_branding)

    response = await tenant_routes.get_current_tenant_branding(
        tenant_id="tenant-1",
        db=object(),
    )

    assert response.tenant_id == "tenant-1"
    assert response.logo_file_key is None
    assert response.logo_url is None
    assert response.brand_primary_color == "#2563EB"
    assert response.brand_secondary_color == "#1D4ED8"
    assert response.sidebar_background_color == "#111827"
    assert response.sidebar_text_color == "#FFFFFF"


@pytest.mark.asyncio
async def test_get_current_tenant_branding_route_preserves_saved_branding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_get_tenant_branding(*_: object, **__: object):
        return tenant_service.TenantBrandingDetails(
            tenant_id="tenant-1",
            logo_file_key="tenant-logos/tenant-1/logo.png",
            logo_url="https://cdn.example.com/logo.png",
            brand_primary_color="#F97316",
            brand_secondary_color="#FDBA74",
            sidebar_background_color="#1E293B",
            sidebar_text_color="#F8FAFC",
        )

    monkeypatch.setattr(tenant_routes, "get_tenant_branding", _fake_get_tenant_branding)

    response = await tenant_routes.get_current_tenant_branding(
        tenant_id="tenant-1",
        db=object(),
    )

    assert response.logo_file_key == "tenant-logos/tenant-1/logo.png"
    assert response.logo_url == "https://cdn.example.com/logo.png"
    assert response.brand_primary_color == "#F97316"
    assert response.brand_secondary_color == "#FDBA74"
    assert response.sidebar_background_color == "#1E293B"
    assert response.sidebar_text_color == "#F8FAFC"


@pytest.mark.asyncio
async def test_update_tenant_details_persists_company_profile_and_currencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeTenantSettingsSession()
    invalidated: list[str] = []

    async def _fake_invalidate(tenant_id: str) -> None:
        invalidated.append(tenant_id)

    monkeypatch.setattr(tenant_service.auth_cache, "invalidate_snapshots_for_tenant", _fake_invalidate)

    tenant = await tenant_service.update_tenant_details(
        session,
        tenant_id="tenant-1",
        name="Northwind CRM",
        legal_name="Northwind Labs AB",
        address_line_1="Sveavagen 2",
        address_line_2="Floor 4",
        city="Stockholm",
        state_region="Stockholm County",
        postal_code="111 58",
        country="Sweden",
        vat_number="SE987654321001",
        default_currency="eur",
        secondary_currency="usd",
        secondary_currency_rate="1.080000",
        brand_primary_color="#F97316",
        brand_secondary_color="#FDBA74",
        sidebar_background_color="#1E293B",
        sidebar_text_color="#F8FAFC",
    )

    assert tenant.name == "Northwind CRM"
    assert tenant.address_line_1 == "Sveavagen 2"
    assert tenant.address_line_2 == "Floor 4"
    assert tenant.default_currency == "EUR"
    assert tenant.secondary_currency == "USD"
    assert str(tenant.secondary_currency_rate) == "1.080000"
    assert tenant.secondary_currency_rate_source == "operator_manual"
    assert tenant.secondary_currency_rate_as_of is not None
    assert tenant.brand_primary_color == "#F97316"
    assert tenant.brand_secondary_color == "#FDBA74"
    assert tenant.sidebar_background_color == "#1E293B"
    assert tenant.sidebar_text_color == "#F8FAFC"
    assert invalidated == ["tenant-1"]

    reloaded = await tenant_service.get_tenant_details(session, tenant_id="tenant-1")

    assert reloaded is not None
    assert reloaded.brand_primary_color == "#F97316"
    assert reloaded.brand_secondary_color == "#FDBA74"
    assert reloaded.sidebar_background_color == "#1E293B"
    assert reloaded.sidebar_text_color == "#F8FAFC"


@pytest.mark.asyncio
async def test_update_tenant_details_rejects_matching_secondary_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeTenantSettingsSession()

    async def _fake_invalidate(_: str) -> None:
        raise AssertionError("Auth cache should not be invalidated on validation failure")

    monkeypatch.setattr(tenant_service.auth_cache, "invalidate_snapshots_for_tenant", _fake_invalidate)

    with pytest.raises(ValueError, match="Secondary currency must differ from the default currency"):
        await tenant_service.update_tenant_details(
            session,
            tenant_id="tenant-1",
            name="Northwind CRM",
            legal_name="Northwind Labs AB",
            address_line_1="Sveavagen 2",
            address_line_2=None,
            city="Stockholm",
            state_region=None,
            postal_code="111 58",
            country="Sweden",
            vat_number="SE987654321001",
            default_currency="EUR",
            secondary_currency="eur",
        )


@pytest.mark.asyncio
async def test_update_tenant_details_rejects_invalid_brand_hex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeTenantSettingsSession()

    async def _fake_invalidate(_: str) -> None:
        raise AssertionError("Auth cache should not be invalidated on validation failure")

    monkeypatch.setattr(tenant_service.auth_cache, "invalidate_snapshots_for_tenant", _fake_invalidate)

    with pytest.raises(ValueError, match="Brand primary color must be a valid hex color in #RRGGBB format"):
        await tenant_service.update_tenant_details(
            session,
            tenant_id="tenant-1",
            name="Northwind CRM",
            legal_name="Northwind Labs AB",
            address_line_1="Sveavagen 2",
            address_line_2=None,
            city="Stockholm",
            state_region=None,
            postal_code="111 58",
            country="Sweden",
            vat_number="SE987654321001",
            default_currency="EUR",
            secondary_currency="USD",
            brand_primary_color="#12FG45",
            brand_secondary_color=None,
            sidebar_background_color="#111827",
            sidebar_text_color="#FFFFFF",
        )


@pytest.mark.asyncio
async def test_update_tenant_details_rejects_rate_without_secondary_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeTenantSettingsSession()

    async def _fake_invalidate(_: str) -> None:
        raise AssertionError("Auth cache should not be invalidated on validation failure")

    monkeypatch.setattr(tenant_service.auth_cache, "invalidate_snapshots_for_tenant", _fake_invalidate)

    with pytest.raises(ValueError, match="Secondary currency rate requires a configured secondary currency"):
        await tenant_service.update_tenant_details(
            session,
            tenant_id="tenant-1",
            name="Northwind CRM",
            legal_name="Northwind Labs AB",
            address_line_1="Sveavagen 2",
            address_line_2=None,
            city="Stockholm",
            state_region=None,
            postal_code="111 58",
            country="Sweden",
            vat_number="SE987654321001",
            default_currency="EUR",
            secondary_currency=None,
            secondary_currency_rate="1.100000",
        )

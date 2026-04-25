from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.security.deps import get_current_principal
from app.db_deps import get_auth_db
from app.main import create_app


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

    def scalar_one(self) -> Any:
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


@dataclass
class FakeSalesRouteSession:
    tenant_id: str = "tenant-alpha"
    user_id: str = "user-alpha"

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "select exists (" in sql and "from public.tenant_user_roles tur" in sql:
            return _FakeResult(scalar=True)

        if "select 1 from public.companies" in sql:
            return _FakeResult(scalar=1)

        if (
            "from public.deals" in sql
            and "where tenant_id = cast(:tenant_id as varchar)" in sql
            and "id = cast(:deal_id as varchar)" in sql
            and "select" in sql
        ):
            return _FakeResult(
                rows=[
                    {
                        "id": str(payload["deal_id"]),
                        "tenant_id": str(payload["tenant_id"]),
                        "name": "Inbound lead",
                        "company_id": "company-1",
                        "contact_id": None,
                        "product_id": None,
                        "amount": Decimal("1250.00"),
                        "currency": "USD",
                        "stage": "new lead",
                        "status": "open",
                        "expected_close_date": None,
                        "notes": None,
                        "next_follow_up_at": None,
                        "follow_up_note": None,
                        "closed_at": None,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                ]
            )

        if "update public.deals set" in sql:
            raise IntegrityError(
                statement,
                params,
                Exception('new row for relation "deals" violates check constraint "ck_deals_stage_valid"'),
            )

        raise AssertionError(f"Unhandled SQL in fake sales route session: {sql}")


@pytest.fixture
def fake_db() -> FakeSalesRouteSession:
    return FakeSalesRouteSession()


@pytest_asyncio.fixture
async def client(fake_db: FakeSalesRouteSession):
    app = create_app()

    async def _override_principal() -> dict[str, Any]:
        return {
            "sub": fake_db.user_id,
            "tenant_id": fake_db.tenant_id,
            "tenant_status": "active",
        }

    async def _override_auth_db():
        yield fake_db

    app.dependency_overrides[get_current_principal] = _override_principal
    app.dependency_overrides[get_auth_db] = _override_auth_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()


def _auth_headers(tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer integration-test-token",
        "X-Tenant-Id": tenant_id,
    }


@pytest.mark.asyncio
async def test_update_deal_route_surfaces_stage_constraint_mismatch_as_client_error(
    client: AsyncClient,
    fake_db: FakeSalesRouteSession,
) -> None:
    response = await client.patch(
        "/sales/deals/deal-123",
        headers=_auth_headers(fake_db.tenant_id),
        json={
            "stage": "qualified lead",
            "status": "open",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "bad_request",
            "message": "Invalid deal stage. The current deal stage contract is out of sync with persistence constraints.",
        }
    }

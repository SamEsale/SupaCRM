from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security.deps import get_current_principal
from app.db_deps import get_auth_db
from app.main import create_app


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _FakeResult:
    def __init__(self, *, rows: list[dict[str, Any]] | None = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise AssertionError("expected scalar result")
        return self._scalar


@dataclass
class FakeInvoicePdfSession:
    tenant_id: str = "tenant-1"

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.tenants = {
            self.tenant_id: {
                "id": self.tenant_id,
                "name": "Northwind Workspace",
                "brand_primary_color": "#2563EB",
                "brand_secondary_color": "#DBEAFE",
            }
        }
        self.companies = {
            "company-1": {
                "id": "company-1",
                "tenant_id": self.tenant_id,
                "name": "Acme AB",
                "email": "billing@acme.test",
                "phone": "+46 8 123 45 67",
                "address": "Sveavagen 1, Stockholm",
                "vat_number": "SE123456789001",
            }
        }
        self.contacts = {
            "contact-1": {
                "id": "contact-1",
                "tenant_id": self.tenant_id,
                "company_id": "company-1",
                "first_name": "Alicia",
                "last_name": "Buyer",
                "email": "alicia@acme.test",
                "phone": "+46 8 765 43 21",
            }
        }
        self.products = {
            "product-1": {
                "id": "product-1",
                "tenant_id": self.tenant_id,
                "name": "CRM Rollout",
                "unit_price": Decimal("1200.00"),
            }
        }
        self.invoices: dict[str, dict[str, Any]] = {}
        self._created_at = now

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "select exists (" in sql and "from public.tenant_user_roles tur" in sql:
            return _FakeResult(scalar=True)

        if "from public.companies" in sql and "id = cast(:company_id as varchar)" in sql:
            company = self.companies.get(str(payload["company_id"]))
            return _FakeResult(scalar=1 if company and company["tenant_id"] == str(payload["tenant_id"]) else None)

        if "from public.contacts" in sql and "id = cast(:contact_id as varchar)" in sql and "select 1" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            return _FakeResult(scalar=1 if contact and contact["tenant_id"] == str(payload["tenant_id"]) else None)

        if "select company_id from public.contacts" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            return _FakeResult(rows=[{"company_id": contact["company_id"]}] if contact else [])

        if "from public.products" in sql and "id = cast(:product_id as varchar)" in sql:
            product = self.products.get(str(payload["product_id"]))
            return _FakeResult(scalar=1 if product and product["tenant_id"] == str(payload["tenant_id"]) else None)

        if "select count(*) + 1 from public.invoices" in sql:
            total = sum(1 for invoice in self.invoices.values() if invoice["tenant_id"] == str(payload["tenant_id"]))
            return _FakeResult(scalar=total + 1)

        if "select 1 from public.invoices where number = cast(:number as varchar)" in sql:
            exists = any(invoice["number"] == str(payload["number"]) for invoice in self.invoices.values())
            return _FakeResult(scalar=1 if exists else None)

        if "select 1 from public.invoices where tenant_id = cast(:tenant_id as varchar) and source_quote_id = cast(:source_quote_id as varchar)" in sql:
            return _FakeResult(scalar=None)

        if "insert into public.invoices" in sql:
            invoice_id = str(payload["id"])
            invoice = {
                "id": invoice_id,
                "tenant_id": str(payload["tenant_id"]),
                "number": str(payload["number"]),
                "company_id": str(payload["company_id"]),
                "contact_id": payload["contact_id"],
                "product_id": payload["product_id"],
                "source_quote_id": payload["source_quote_id"],
                "subscription_id": payload["subscription_id"],
                "billing_cycle_id": payload["billing_cycle_id"],
                "issue_date": payload["issue_date"],
                "due_date": payload["due_date"],
                "currency": str(payload["currency"]),
                "total_amount": Decimal(str(payload["total_amount"])),
                "status": str(payload["status"]),
                "notes": payload["notes"],
                "created_at": self._created_at,
                "updated_at": self._created_at,
            }
            self.invoices[invoice_id] = invoice
            return _FakeResult(rows=[invoice])

        if "from public.invoices i" in sql and "join public.tenants t" in sql:
            invoice = self.invoices.get(str(payload["invoice_id"]))
            if not invoice or invoice["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])

            tenant = self.tenants[invoice["tenant_id"]]
            company = self.companies[invoice["company_id"]]
            contact = self.contacts.get(invoice["contact_id"]) if invoice["contact_id"] else None
            product = self.products.get(invoice["product_id"]) if invoice["product_id"] else None
            return _FakeResult(
                rows=[
                    {
                        "invoice_id": invoice["id"],
                        "invoice_number": invoice["number"],
                        "issue_date": invoice["issue_date"],
                        "due_date": invoice["due_date"],
                        "currency": invoice["currency"],
                        "status": invoice["status"],
                        "total_amount": invoice["total_amount"],
                        "notes": invoice["notes"],
                        "tenant_name": tenant["name"],
                        "brand_primary_color": tenant["brand_primary_color"],
                        "brand_secondary_color": tenant["brand_secondary_color"],
                        "company_name": company["name"],
                        "company_email": company["email"],
                        "company_phone": company["phone"],
                        "company_address": company["address"],
                        "company_vat_number": company["vat_number"],
                        "contact_first_name": contact["first_name"] if contact else None,
                        "contact_last_name": contact["last_name"] if contact else None,
                        "contact_email": contact["email"] if contact else None,
                        "contact_phone": contact["phone"] if contact else None,
                        "product_name": product["name"] if product else None,
                        "product_unit_price": product["unit_price"] if product else None,
                    }
                ]
            )

        raise AssertionError(f"Unhandled SQL in fake invoice pdf session: {sql}")

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def close(self) -> None:
        return None


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    app = create_app()
    session = FakeInvoicePdfSession()

    async def _override_principal() -> dict[str, Any]:
        return {
            "sub": "user-1",
            "tenant_id": session.tenant_id,
            "tenant_status": "active",
        }

    async def _override_auth_db():
        yield session

    app.dependency_overrides[get_current_principal] = _override_principal
    app.dependency_overrides[get_auth_db] = _override_auth_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invoice_pdf_download_returns_non_empty_pdf(client: AsyncClient) -> None:
    headers = {
        "Authorization": "Bearer integration-test-token",
        "X-Tenant-Id": "tenant-1",
    }

    create_response = await client.post(
        "/invoices",
        headers=headers,
        json={
            "company_id": "company-1",
            "contact_id": "contact-1",
            "product_id": "product-1",
            "issue_date": date(2026, 4, 1).isoformat(),
            "due_date": date(2026, 4, 30).isoformat(),
            "currency": "USD",
            "total_amount": "1200.00",
            "notes": "PDF smoke test invoice",
        },
    )

    assert create_response.status_code == 200
    invoice_id = create_response.json()["id"]

    pdf_response = await client.get(
        f"/finance/invoices/{invoice_id}/pdf",
        headers=headers,
    )

    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert len(pdf_response.content) > 100
    assert pdf_response.content.startswith(b"%PDF")

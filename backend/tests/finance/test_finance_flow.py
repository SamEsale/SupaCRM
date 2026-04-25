from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.invoicing.service import create_invoice
from app.quotes.service import create_quote
from app.reporting.service import get_revenue_flow_report


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _FakeResult:
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        scalar: Any = None,
        first_row: Any = None,
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar
        self._first_row = first_row

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise AssertionError("expected scalar result")
        return self._scalar

    def first(self) -> Any:
        if self._first_row is not None:
            return self._first_row
        return self._rows[0] if self._rows else None


class FakeFinanceSession:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.companies = {
            "company-1": {"id": "company-1", "tenant_id": "tenant-1"},
            "company-2": {"id": "company-2", "tenant_id": "tenant-1"},
            "company-x": {"id": "company-x", "tenant_id": "tenant-2"},
        }
        self.contacts = {
            "contact-1": {"id": "contact-1", "tenant_id": "tenant-1", "company_id": "company-1"},
            "contact-2": {"id": "contact-2", "tenant_id": "tenant-1", "company_id": "company-2"},
        }
        self.products = {
            "product-1": {"id": "product-1", "tenant_id": "tenant-1"},
        }
        self.deals = {
            "deal-1": {
                "id": "deal-1",
                "tenant_id": "tenant-1",
                "name": "Northwind renewal",
                "company_id": "company-1",
                "contact_id": "contact-1",
                "product_id": "product-1",
                "amount": Decimal("400.00"),
                "currency": "USD",
                "stage": "qualified lead",
                "status": "in progress",
                "expected_close_date": None,
                "notes": "Warm opportunity",
                "next_follow_up_at": now + timedelta(days=2),
                "follow_up_note": None,
                "closed_at": None,
                "created_at": now,
                "updated_at": now,
            },
            "deal-won": {
                "id": "deal-won",
                "tenant_id": "tenant-1",
                "name": "Signed rollout",
                "company_id": "company-1",
                "contact_id": "contact-1",
                "product_id": None,
                "amount": Decimal("900.00"),
                "currency": "USD",
                "stage": "contract signed",
                "status": "won",
                "expected_close_date": None,
                "notes": None,
                "next_follow_up_at": None,
                "follow_up_note": None,
                "closed_at": now - timedelta(days=5),
                "created_at": now - timedelta(days=10),
                "updated_at": now - timedelta(days=5),
            },
            "deal-lost": {
                "id": "deal-lost",
                "tenant_id": "tenant-1",
                "name": "Lost expansion",
                "company_id": "company-2",
                "contact_id": "contact-2",
                "product_id": None,
                "amount": Decimal("250.00"),
                "currency": "USD",
                "stage": "deal not secured",
                "status": "lost",
                "expected_close_date": None,
                "notes": None,
                "next_follow_up_at": None,
                "follow_up_note": None,
                "closed_at": now - timedelta(days=3),
                "created_at": now - timedelta(days=8),
                "updated_at": now - timedelta(days=3),
            },
            "deal-other-tenant": {
                "id": "deal-other-tenant",
                "tenant_id": "tenant-2",
                "name": "Outside tenant",
                "company_id": "company-x",
                "contact_id": None,
                "product_id": None,
                "amount": Decimal("999.00"),
                "currency": "EUR",
                "stage": "qualified lead",
                "status": "open",
                "expected_close_date": None,
                "notes": None,
                "next_follow_up_at": None,
                "follow_up_note": None,
                "closed_at": None,
                "created_at": now,
                "updated_at": now,
            },
        }
        self.quotes: dict[str, dict[str, Any]] = {
            "quote-seeded": {
                "id": "quote-seeded",
                "tenant_id": "tenant-1",
                "number": "QTE-000001",
                "company_id": "company-1",
                "contact_id": "contact-1",
                "deal_id": "deal-1",
                "source_deal_id": "deal-1",
                "product_id": "product-1",
                "issue_date": date.today(),
                "expiry_date": date.today() + timedelta(days=14),
                "currency": "USD",
                "total_amount": Decimal("400.00"),
                "status": "accepted",
                "notes": "Seeded quote",
                "created_at": now - timedelta(days=2),
                "updated_at": now - timedelta(days=2),
            },
            "quote-accepted-open": {
                "id": "quote-accepted-open",
                "tenant_id": "tenant-1",
                "number": "QTE-000002",
                "company_id": "company-1",
                "contact_id": "contact-1",
                "deal_id": "deal-1",
                "source_deal_id": "deal-1",
                "product_id": "product-1",
                "issue_date": date.today(),
                "expiry_date": date.today() + timedelta(days=21),
                "currency": "USD",
                "total_amount": Decimal("450.00"),
                "status": "accepted",
                "notes": "Accepted and ready for invoicing",
                "created_at": now - timedelta(days=1),
                "updated_at": now - timedelta(days=1),
            },
            "quote-draft-open": {
                "id": "quote-draft-open",
                "tenant_id": "tenant-1",
                "number": "QTE-000003",
                "company_id": "company-1",
                "contact_id": "contact-1",
                "deal_id": "deal-1",
                "source_deal_id": "deal-1",
                "product_id": "product-1",
                "issue_date": date.today(),
                "expiry_date": date.today() + timedelta(days=21),
                "currency": "USD",
                "total_amount": Decimal("275.00"),
                "status": "draft",
                "notes": "Still in draft",
                "created_at": now - timedelta(hours=12),
                "updated_at": now - timedelta(hours=12),
            },
        }
        self.invoices: dict[str, dict[str, Any]] = {
            "invoice-seeded": {
                "id": "invoice-seeded",
                "tenant_id": "tenant-1",
                "number": "INV-000001",
                "company_id": "company-1",
                "contact_id": "contact-1",
                "product_id": "product-1",
                "source_quote_id": "quote-seeded",
                "subscription_id": None,
                "billing_cycle_id": None,
                "issue_date": date.today(),
                "due_date": date.today() + timedelta(days=30),
                "currency": "USD",
                "total_amount": Decimal("400.00"),
                "status": "issued",
                "notes": "Seeded invoice",
                "created_at": now - timedelta(days=1),
                "updated_at": now - timedelta(days=1),
            },
            "invoice-paid": {
                "id": "invoice-paid",
                "tenant_id": "tenant-1",
                "number": "INV-000002",
                "company_id": "company-1",
                "contact_id": "contact-1",
                "product_id": None,
                "source_quote_id": "quote-seeded",
                "subscription_id": None,
                "billing_cycle_id": None,
                "issue_date": date.today(),
                "due_date": date.today() + timedelta(days=15),
                "currency": "USD",
                "total_amount": Decimal("900.00"),
                "status": "paid",
                "notes": "Collected",
                "created_at": now - timedelta(days=4),
                "updated_at": now - timedelta(days=2),
            },
        }

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "select 1 from public.companies" in sql:
            company = self.companies.get(str(payload["company_id"]))
            if company and company["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select 1 from public.contacts" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            if contact and contact["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select company_id from public.contacts" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            if contact and contact["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(rows=[{"company_id": contact["company_id"]}])
            return _FakeResult(rows=[])

        if "select 1 from public.products" in sql:
            product = self.products.get(str(payload["product_id"]))
            if product and product["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select 1 from public.deals" in sql:
            deal = self.deals.get(str(payload["deal_id"]))
            if deal and deal["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if (
            "from public.deals where tenant_id = cast(:tenant_id as varchar) and id = cast(:deal_id as varchar)" in sql
            and "select" in sql
        ):
            deal = self.deals.get(str(payload["deal_id"]))
            if not deal or deal["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(deal)])

        if "select 1 from public.quotes where number = cast(:number as varchar)" in sql:
            exists = any(quote["number"] == str(payload["number"]) for quote in self.quotes.values())
            return _FakeResult(scalar=1 if exists else None)

        if "select count(*) + 1 from public.quotes" in sql:
            tenant_quotes = [quote for quote in self.quotes.values() if quote["tenant_id"] == str(payload["tenant_id"])]
            return _FakeResult(scalar=len(tenant_quotes) + 1)

        if "insert into public.quotes" in sql:
            now = datetime.now(timezone.utc)
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "number": str(payload["number"]),
                "company_id": str(payload["company_id"]),
                "contact_id": payload.get("contact_id"),
                "deal_id": payload.get("deal_id"),
                "source_deal_id": payload.get("source_deal_id"),
                "product_id": payload.get("product_id"),
                "issue_date": payload["issue_date"],
                "expiry_date": payload["expiry_date"],
                "currency": str(payload["currency"]),
                "total_amount": Decimal(str(payload["total_amount"])),
                "status": str(payload["status"]),
                "notes": payload.get("notes"),
                "created_at": now,
                "updated_at": now,
            }
            self.quotes[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "select 1 from public.quotes where tenant_id = cast(:tenant_id as varchar) and id = cast(:quote_id as varchar)" in sql:
            quote = self.quotes.get(str(payload["quote_id"]))
            if quote and quote["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select company_id from public.quotes" in sql:
            quote = self.quotes.get(str(payload["quote_id"]))
            if quote and quote["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(rows=[{"company_id": quote["company_id"]}])
            return _FakeResult(rows=[])

        if "select company_id, status from public.quotes" in sql:
            quote = self.quotes.get(str(payload["quote_id"]))
            if quote and quote["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(
                    rows=[{"company_id": quote["company_id"], "status": quote["status"]}]
                )
            return _FakeResult(rows=[])

        if "select 1 from public.invoices where tenant_id = cast(:tenant_id as varchar) and source_quote_id = cast(:source_quote_id as varchar)" in sql:
            exists = any(
                invoice["tenant_id"] == str(payload["tenant_id"])
                and invoice.get("source_quote_id") == str(payload["source_quote_id"])
                for invoice in self.invoices.values()
            )
            return _FakeResult(scalar=1 if exists else None)

        if "select count(*) + 1 from public.invoices" in sql:
            tenant_invoices = [invoice for invoice in self.invoices.values() if invoice["tenant_id"] == str(payload["tenant_id"])]
            return _FakeResult(scalar=len(tenant_invoices) + 1)

        if "select 1 from public.invoices where number = cast(:number as varchar)" in sql:
            exists = any(invoice["number"] == str(payload["number"]) for invoice in self.invoices.values())
            return _FakeResult(scalar=1 if exists else None)

        if "insert into public.invoices" in sql:
            now = datetime.now(timezone.utc)
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "number": str(payload["number"]),
                "company_id": str(payload["company_id"]),
                "contact_id": payload.get("contact_id"),
                "product_id": payload.get("product_id"),
                "source_quote_id": payload.get("source_quote_id"),
                "subscription_id": payload.get("subscription_id"),
                "billing_cycle_id": payload.get("billing_cycle_id"),
                "issue_date": payload["issue_date"],
                "due_date": payload["due_date"],
                "currency": str(payload["currency"]),
                "total_amount": Decimal(str(payload["total_amount"])),
                "status": str(payload["status"]),
                "notes": payload.get("notes"),
                "created_at": now,
                "updated_at": now,
            }
            self.invoices[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "select status, total_amount, currency, created_at from public.quotes" in sql:
            tenant_id = str(payload["tenant_id"])
            rows = [
                {
                    "status": quote["status"],
                    "total_amount": quote["total_amount"],
                    "currency": quote["currency"],
                    "created_at": quote["created_at"],
                }
                for quote in self.quotes.values()
                if quote["tenant_id"] == tenant_id
            ]
            return _FakeResult(rows=rows)

        if "select status, total_amount, currency, created_at from public.invoices" in sql:
            tenant_id = str(payload["tenant_id"])
            rows = [
                {
                    "status": invoice["status"],
                    "total_amount": invoice["total_amount"],
                    "currency": invoice["currency"],
                    "created_at": invoice["created_at"],
                }
                for invoice in self.invoices.values()
                if invoice["tenant_id"] == tenant_id
            ]
            return _FakeResult(rows=rows)

        if "select stage, status, amount, currency, next_follow_up_at, closed_at" in sql:
            tenant_id = str(payload["tenant_id"])
            rows = [
                {
                    "stage": deal["stage"],
                    "status": deal["status"],
                    "amount": deal["amount"],
                    "currency": deal["currency"],
                    "next_follow_up_at": deal["next_follow_up_at"],
                    "closed_at": deal["closed_at"],
                }
                for deal in self.deals.values()
                if deal["tenant_id"] == tenant_id
            ]
            return _FakeResult(rows=rows)

        raise AssertionError(f"Unhandled SQL in FakeFinanceSession: {sql}")


@pytest.fixture
def session() -> FakeFinanceSession:
    return FakeFinanceSession()


@pytest.mark.asyncio
async def test_create_quote_preserves_source_deal_and_blocks_contact_company_mismatch(
    session: FakeFinanceSession,
) -> None:
    created = await create_quote(
        session,
        tenant_id="tenant-1",
        company_id="company-1",
        contact_id="contact-1",
        deal_id="deal-1",
        source_deal_id="deal-1",
        product_id="product-1",
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=30),
        currency="usd",
        total_amount=Decimal("400.00"),
        status="draft",
        notes="Prepared from deal",
    )

    assert created.company_id == "company-1"
    assert created.deal_id == "deal-1"
    assert created.source_deal_id == "deal-1"
    assert created.number == "QTE-000004"

    with pytest.raises(ValueError, match="Contact does not belong to company"):
        await create_quote(
            session,
            tenant_id="tenant-1",
            company_id="company-1",
            contact_id="contact-2",
            deal_id="deal-1",
            source_deal_id="deal-1",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            currency="usd",
            total_amount=Decimal("400.00"),
            status="draft",
        )


@pytest.mark.asyncio
async def test_create_invoice_preserves_source_quote_and_blocks_company_mismatch(
    session: FakeFinanceSession,
) -> None:
    created = await create_invoice(
        session,
        tenant_id="tenant-1",
        company_id="company-1",
        contact_id="contact-1",
        product_id="product-1",
        source_quote_id="quote-accepted-open",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        currency="usd",
        total_amount=Decimal("400.00"),
        notes="Prepared from quote",
    )

    assert created.source_quote_id == "quote-accepted-open"
    assert created.company_id == "company-1"
    assert created.number == "INV-000003"

    with pytest.raises(ValueError, match="Quote does not belong to company"):
        await create_invoice(
            session,
            tenant_id="tenant-1",
            company_id="company-2",
            contact_id="contact-2",
            source_quote_id="quote-accepted-open",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            currency="usd",
            total_amount=Decimal("400.00"),
        )


@pytest.mark.asyncio
async def test_create_invoice_rejects_non_accepted_source_quote(
    session: FakeFinanceSession,
) -> None:
    with pytest.raises(ValueError, match="Only accepted quotes can be linked to invoices"):
        await create_invoice(
            session,
            tenant_id="tenant-1",
            company_id="company-1",
            contact_id="contact-1",
            product_id="product-1",
            source_quote_id="quote-draft-open",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            currency="usd",
            total_amount=Decimal("275.00"),
            notes="Attempted from draft quote",
        )


@pytest.mark.asyncio
async def test_create_invoice_rejects_duplicate_source_quote_invoice(
    session: FakeFinanceSession,
) -> None:
    with pytest.raises(ValueError, match="Invoice already exists for source quote"):
        await create_invoice(
            session,
            tenant_id="tenant-1",
            company_id="company-1",
            contact_id="contact-1",
            product_id="product-1",
            source_quote_id="quote-seeded",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            currency="usd",
            total_amount=Decimal("400.00"),
            notes="Attempted duplicate invoice",
        )


@pytest.mark.asyncio
async def test_revenue_flow_report_is_tenant_scoped_and_keeps_commercial_story_coherent(
    session: FakeFinanceSession,
) -> None:
    report = await get_revenue_flow_report(session, tenant_id="tenant-1")

    assert report.sales_report.summary.total_open_pipeline_amount == Decimal("400.00")
    assert report.sales_report.summary.weighted_pipeline_amount == Decimal("100.00")
    assert report.sales_report.summary.won_amount == Decimal("900.00")
    assert report.sales_report.summary.lost_amount == Decimal("250.00")

    assert report.summary.quote_count == 3
    assert report.summary.invoice_count == 2
    assert report.summary.invoice_issued_count == 1
    assert report.summary.invoice_paid_count == 1
    assert report.summary.invoice_overdue_count == 0
    assert report.summary.quote_currencies == ["USD"]
    assert report.summary.invoice_currencies == ["USD"]

    quote_statuses = {item.status: item for item in report.quote_status_breakdown}
    invoice_statuses = {item.status: item for item in report.invoice_status_breakdown}

    assert quote_statuses["accepted"].count == 2
    assert quote_statuses["accepted"].total_amount == Decimal("850.00")
    assert quote_statuses["draft"].count == 1
    assert quote_statuses["draft"].total_amount == Decimal("275.00")
    assert invoice_statuses["issued"].count == 1
    assert invoice_statuses["paid"].count == 1

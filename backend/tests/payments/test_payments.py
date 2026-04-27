from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import os
from typing import Any

import pytest

os.environ["DEBUG"] = "false"

from app.api import api_router
from app.payments.routes import get_invoice_payment_summary_route, list_payments_route
from app.payments.service import (
    create_invoice_payment,
    get_invoice_payment_summary,
    list_invoice_payments,
)
from app.reporting.service import get_finance_reports_snapshot


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

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise AssertionError("Expected scalar result")
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakePaymentsSession:
    def __init__(self) -> None:
        self.now = datetime(2026, 4, 13, 10, 0, tzinfo=UTC)
        self.invoices: dict[str, dict[str, Any]] = {
            "invoice-1": {
                "id": "invoice-1",
                "tenant_id": "tenant-1",
                "number": "INV-000101",
                "currency": "USD",
                "total_amount": Decimal("100.00"),
                "status": "issued",
                "issue_date": date(2026, 4, 13),
                "notes": "Primary invoice",
            },
            "invoice-2": {
                "id": "invoice-2",
                "tenant_id": "tenant-1",
                "number": "INV-000102",
                "currency": "USD",
                "total_amount": Decimal("200.00"),
                "status": "overdue",
                "issue_date": date(2026, 4, 10),
                "notes": None,
            },
            "invoice-other": {
                "id": "invoice-other",
                "tenant_id": "tenant-2",
                "number": "INV-900101",
                "currency": "EUR",
                "total_amount": Decimal("90.00"),
                "status": "issued",
                "issue_date": date(2026, 4, 11),
                "notes": None,
            },
        }
        self.invoice_payments: dict[str, dict[str, Any]] = {
            "payment-seeded": {
                "id": "payment-seeded",
                "tenant_id": "tenant-1",
                "invoice_id": "invoice-2",
                "amount": Decimal("60.00"),
                "currency": "USD",
                "method": "bank_transfer",
                "status": "completed",
                "payment_date": datetime(2026, 4, 12, 9, 0, tzinfo=UTC),
                "external_reference": "BT-060",
                "notes": "Deposit",
                "created_at": self.now,
                "updated_at": self.now,
            },
            "payment-pending": {
                "id": "payment-pending",
                "tenant_id": "tenant-1",
                "invoice_id": "invoice-2",
                "amount": Decimal("20.00"),
                "currency": "USD",
                "method": "cash",
                "status": "pending",
                "payment_date": datetime(2026, 4, 12, 15, 0, tzinfo=UTC),
                "external_reference": None,
                "notes": None,
                "created_at": self.now,
                "updated_at": self.now,
            },
            "payment-other-tenant": {
                "id": "payment-other-tenant",
                "tenant_id": "tenant-2",
                "invoice_id": "invoice-other",
                "amount": Decimal("90.00"),
                "currency": "EUR",
                "method": "other",
                "status": "completed",
                "payment_date": datetime(2026, 4, 12, 12, 0, tzinfo=UTC),
                "external_reference": None,
                "notes": None,
                "created_at": self.now,
                "updated_at": self.now,
            },
        }

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "from public.invoices" in sql and "where tenant_id = cast(:tenant_id as varchar)" in sql and "id = cast(:invoice_id as varchar)" in sql:
            invoice = self.invoices.get(str(payload["invoice_id"]))
            if not invoice or invoice["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(invoice)])

        if "select coalesce(sum(amount), 0)" in sql and "from public.invoice_payments" in sql:
            completed_sum = sum(
                payment["amount"]
                for payment in self.invoice_payments.values()
                if payment["tenant_id"] == str(payload["tenant_id"])
                and payment["invoice_id"] == str(payload["invoice_id"])
                and payment["status"] == "completed"
            )
            return _FakeResult(scalar=completed_sum)

        if "select 1 from public.invoice_payments" in sql and "limit 1" in sql:
            exists = any(
                payment["tenant_id"] == str(payload["tenant_id"])
                and payment["invoice_id"] == str(payload["invoice_id"])
                for payment in self.invoice_payments.values()
            )
            return _FakeResult(scalar=1 if exists else None)

        if "count(*) as payment_count" in sql and "from public.invoice_payments" in sql:
            matching = [
                payment
                for payment in self.invoice_payments.values()
                if payment["tenant_id"] == str(payload["tenant_id"])
                and payment["invoice_id"] == str(payload["invoice_id"])
            ]
            return _FakeResult(
                rows=[
                    {
                        "payment_count": len(matching),
                        "completed_amount": sum(
                            payment["amount"] for payment in matching if payment["status"] == "completed"
                        ),
                        "pending_amount": sum(
                            payment["amount"] for payment in matching if payment["status"] == "pending"
                        ),
                        "completed_payment_count": sum(
                            1 for payment in matching if payment["status"] == "completed"
                        ),
                        "pending_payment_count": sum(
                            1 for payment in matching if payment["status"] == "pending"
                        ),
                    }
                ]
            )

        if "insert into public.invoice_payments" in sql:
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "invoice_id": str(payload["invoice_id"]),
                "amount": Decimal(str(payload["amount"])),
                "currency": str(payload["currency"]),
                "method": str(payload["method"]),
                "status": str(payload["status"]),
                "payment_date": payload["payment_date"],
                "external_reference": payload["external_reference"],
                "notes": payload["notes"],
                "created_at": self.now,
                "updated_at": self.now,
            }
            self.invoice_payments[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "update public.invoices" in sql and "set status = cast(:status as varchar)" in sql:
            invoice = self.invoices[str(payload["invoice_id"])]
            invoice["status"] = str(payload["status"])
            return _FakeResult(rows=[])

        if "select count(*) from public.invoice_payments" in sql:
            matching = self._filter_payments(payload)
            return _FakeResult(scalar=len(matching))

        if "select id, tenant_id, invoice_id, amount, currency, method, status, payment_date, external_reference, notes, created_at, updated_at from public.invoice_payments" in sql:
            matching = self._filter_payments(payload)
            matching.sort(key=lambda item: (item["payment_date"], item["created_at"], item["id"]), reverse=True)
            offset = int(payload.get("offset", 0))
            limit = int(payload.get("limit", len(matching)))
            return _FakeResult(rows=[dict(row) for row in matching[offset : offset + limit]])

        if "select status, amount, currency, payment_date from public.invoice_payments" in sql:
            matching = [
                {
                    "status": payment["status"],
                    "amount": payment["amount"],
                    "currency": payment["currency"],
                    "payment_date": payment["payment_date"],
                }
                for payment in self.invoice_payments.values()
                if payment["tenant_id"] == str(payload["tenant_id"])
            ]
            return _FakeResult(rows=matching)

        raise AssertionError(f"Unhandled SQL in FakePaymentsSession: {sql}")

    def _filter_payments(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        tenant_id = str(payload["tenant_id"])
        invoice_id = payload.get("invoice_id")
        status = payload.get("status")
        method = payload.get("method")

        rows = [payment for payment in self.invoice_payments.values() if payment["tenant_id"] == tenant_id]
        if invoice_id:
            rows = [payment for payment in rows if payment["invoice_id"] == str(invoice_id)]
        if status:
            rows = [payment for payment in rows if payment["status"] == str(status)]
        if method:
            rows = [payment for payment in rows if payment["method"] == str(method)]
        return rows


@pytest.mark.asyncio
async def test_create_completed_payment_updates_invoice_and_posts_accounting(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakePaymentsSession()
    calls: list[dict[str, Any]] = []

    async def _record_posting(*args: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("app.payments.service.sync_payment_accounting_entries", _record_posting)

    payment = await create_invoice_payment(
        session,
        tenant_id="tenant-1",
        invoice_id="invoice-1",
        amount=Decimal("100.00"),
        currency="USD",
        method="bank_transfer",
        status="completed",
        payment_date=datetime(2026, 4, 13, 10, 30, tzinfo=UTC),
        external_reference="BT-100",
        notes="Full settlement",
    )

    assert payment.invoice_id == "invoice-1"
    assert payment.status == "completed"
    assert session.invoices["invoice-1"]["status"] == "paid"
    assert len(calls) == 1
    assert calls[0]["payment_id"] == payment.id
    assert calls[0]["invoice_id"] == "invoice-1"
    assert calls[0]["amount"] == Decimal("100.00")


@pytest.mark.asyncio
async def test_create_invoice_payment_blocks_overpayment() -> None:
    session = FakePaymentsSession()

    with pytest.raises(ValueError, match="Payment amount exceeds the outstanding invoice balance"):
        await create_invoice_payment(
            session,
            tenant_id="tenant-1",
            invoice_id="invoice-2",
            amount=Decimal("150.00"),
            currency="USD",
            method="bank_transfer",
            status="completed",
            payment_date=datetime(2026, 4, 13, 11, 0, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_create_invoice_payment_requires_tenant_scoped_invoice() -> None:
    session = FakePaymentsSession()

    with pytest.raises(ValueError, match="Invoice does not exist: invoice-other"):
        await create_invoice_payment(
            session,
            tenant_id="tenant-1",
            invoice_id="invoice-other",
            amount=Decimal("90.00"),
            currency="EUR",
            method="other",
            status="completed",
            payment_date=datetime(2026, 4, 13, 11, 0, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_list_invoice_payments_filters_by_invoice_status_and_method() -> None:
    session = FakePaymentsSession()

    result = await list_invoice_payments(
        session,
        tenant_id="tenant-1",
        invoice_id="invoice-2",
        status="completed",
        method="bank_transfer",
        limit=50,
        offset=0,
    )

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].id == "payment-seeded"


@pytest.mark.asyncio
async def test_list_payments_route_returns_tenant_scoped_records() -> None:
    response = await list_payments_route(
        invoice_id="invoice-2",
        status_filter="completed",
        method="bank_transfer",
        limit=50,
        offset=0,
        tenant_id="tenant-1",
        db=FakePaymentsSession(),
    )

    assert response.total == 1
    assert len(response.items) == 1
    assert response.items[0].id == "payment-seeded"
    assert response.items[0].tenant_id == "tenant-1"


@pytest.mark.asyncio
async def test_get_invoice_payment_summary_route_returns_invoice_payment_summary() -> None:
    response = await get_invoice_payment_summary_route(
        invoice_id="invoice-2",
        tenant_id="tenant-1",
        db=FakePaymentsSession(),
    )

    assert response.invoice_id == "invoice-2"
    assert response.currency == "USD"
    assert response.completed_amount == Decimal("60.00")
    assert response.pending_amount == Decimal("20.00")
    assert response.payment_state == "partially paid"


def test_payments_routes_are_registered_on_api_router() -> None:
    paths = {route.path for route in api_router.routes}

    assert "/payments" in paths
    assert "/payments/invoices/{invoice_id}/summary" in paths


@pytest.mark.asyncio
async def test_finance_reports_snapshot_includes_payment_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakePaymentsSession()

    async def _fake_revenue_flow_report(*args: Any, **kwargs: Any) -> dict[str, str]:
        return {"kind": "revenue-flow"}

    async def _fake_financial_statements(*args: Any, **kwargs: Any) -> dict[str, str]:
        return {"kind": "financial-statements"}

    monkeypatch.setattr("app.reporting.service.get_revenue_flow_report", _fake_revenue_flow_report)
    monkeypatch.setattr("app.reporting.service.get_financial_statements_report", _fake_financial_statements)

    snapshot = await get_finance_reports_snapshot(session, tenant_id="tenant-1")

    assert snapshot.revenue_flow == {"kind": "revenue-flow"}
    assert snapshot.financial_statements == {"kind": "financial-statements"}
    assert snapshot.payments_summary.payment_count == 2
    assert snapshot.payments_summary.completed_payment_count == 1
    assert snapshot.payments_summary.completed_payment_amount == Decimal("60.00")
    assert snapshot.payments_summary.pending_payment_count == 1
    assert snapshot.payments_summary.payment_currencies == ["USD"]
    assert [item.status for item in snapshot.payment_status_breakdown] == ["completed", "pending"]


@pytest.mark.asyncio
async def test_invoice_payment_summary_reports_partial_payment_state() -> None:
    session = FakePaymentsSession()

    summary = await get_invoice_payment_summary(
        session,
        tenant_id="tenant-1",
        invoice_id="invoice-2",
    )

    assert summary.completed_amount == Decimal("60.00")
    assert summary.pending_amount == Decimal("20.00")
    assert summary.outstanding_amount == Decimal("140.00")
    assert summary.payment_state == "partially paid"

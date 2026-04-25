from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import os
from typing import Any

import pytest

os.environ["DEBUG"] = "false"

from app.expenses.routes import list_expenses_route
from app.expenses.service import create_expense, list_expenses, update_expense
from app.tenants.fx import convert_tenant_secondary_currency_amount


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
        return self._scalar


class FakeExpensesSession:
    def __init__(self) -> None:
        self.now = datetime(2026, 4, 14, 10, 0, tzinfo=UTC)
        self.expenses: dict[str, dict[str, Any]] = {
            "expense-1": {
                "id": "expense-1",
                "tenant_id": "tenant-1",
                "title": "Meta ads",
                "description": "Launch campaign spend",
                "amount": Decimal("120.00"),
                "currency": "USD",
                "expense_date": date(2026, 4, 12),
                "category": "marketing",
                "status": "submitted",
                "vendor_name": "Meta",
                "created_at": self.now,
                "updated_at": self.now,
            },
            "expense-2": {
                "id": "expense-2",
                "tenant_id": "tenant-1",
                "title": "Office rent",
                "description": None,
                "amount": Decimal("850.00"),
                "currency": "SEK",
                "expense_date": date(2026, 4, 10),
                "category": "operations",
                "status": "paid",
                "vendor_name": "North Property",
                "created_at": self.now,
                "updated_at": self.now,
            },
            "expense-other": {
                "id": "expense-other",
                "tenant_id": "tenant-2",
                "title": "External",
                "description": None,
                "amount": Decimal("42.00"),
                "currency": "EUR",
                "expense_date": date(2026, 4, 11),
                "category": "operations",
                "status": "draft",
                "vendor_name": None,
                "created_at": self.now,
                "updated_at": self.now,
            },
        }

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "select count(*) from public.expenses" in sql:
            return _FakeResult(scalar=len(self._filter_expenses(payload)))

        if "from public.expenses" in sql and "where tenant_id = cast(:tenant_id as varchar)" in sql and "id = cast(:expense_id as varchar)" in sql:
            expense = self.expenses.get(str(payload["expense_id"]))
            if not expense or expense["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(expense)])

        if "select id, tenant_id, title, description, amount, currency, expense_date, category, status, vendor_name, created_at, updated_at from public.expenses" in sql:
            rows = self._filter_expenses(payload)
            rows.sort(key=lambda item: (item["expense_date"], item["created_at"], item["id"]), reverse=True)
            offset = int(payload.get("offset", 0))
            limit = int(payload.get("limit", len(rows)))
            return _FakeResult(rows=[dict(row) for row in rows[offset : offset + limit]])

        if "insert into public.expenses" in sql:
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "title": str(payload["title"]),
                "description": payload["description"],
                "amount": Decimal(str(payload["amount"])),
                "currency": str(payload["currency"]),
                "expense_date": payload["expense_date"],
                "category": str(payload["category"]),
                "status": str(payload["status"]),
                "vendor_name": payload["vendor_name"],
                "created_at": self.now,
                "updated_at": self.now,
            }
            self.expenses[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "update public.expenses" in sql and "returning" in sql:
            expense = self.expenses.get(str(payload["expense_id"]))
            if not expense or expense["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            expense.update(
                {
                    "title": str(payload["title"]),
                    "description": payload["description"],
                    "amount": Decimal(str(payload["amount"])),
                    "currency": str(payload["currency"]),
                    "expense_date": payload["expense_date"],
                    "category": str(payload["category"]),
                    "status": str(payload["status"]),
                    "vendor_name": payload["vendor_name"],
                    "updated_at": self.now,
                }
            )
            return _FakeResult(rows=[dict(expense)])

        raise AssertionError(f"Unhandled SQL in FakeExpensesSession: {sql}")

    def _filter_expenses(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        tenant_id = str(payload["tenant_id"])
        status = payload.get("status")
        category = payload.get("category")

        rows = [expense for expense in self.expenses.values() if expense["tenant_id"] == tenant_id]
        if status:
            rows = [expense for expense in rows if expense["status"] == str(status)]
        if category:
            rows = [expense for expense in rows if expense["category"].lower() == str(category).lower()]
        return rows


@pytest.mark.asyncio
async def test_list_expenses_is_tenant_scoped_and_filterable() -> None:
    result = await list_expenses(
        FakeExpensesSession(),
        tenant_id="tenant-1",
        status="submitted",
        limit=50,
        offset=0,
    )

    assert result.total == 1
    assert [item.id for item in result.items] == ["expense-1"]


@pytest.mark.asyncio
async def test_list_expenses_route_responds_with_tenant_scoped_items() -> None:
    response = await list_expenses_route(
        status_filter=None,
        category=None,
        limit=100,
        offset=0,
        tenant_id="tenant-1",
        db=FakeExpensesSession(),
    )

    assert response.total == 2
    assert [item.id for item in response.items] == ["expense-1", "expense-2"]
    assert all(item.tenant_id == "tenant-1" for item in response.items)


@pytest.mark.asyncio
async def test_create_paid_expense_posts_accounting(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeExpensesSession()
    calls: list[dict[str, Any]] = []

    async def _record_posting(*args: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("app.expenses.service.sync_expense_accounting_entries", _record_posting)

    expense = await create_expense(
        session,
        tenant_id="tenant-1",
        title="Cloud hosting",
        description="April infra bill",
        amount=Decimal("199.00"),
        currency="usd",
        expense_date=date(2026, 4, 14),
        category="operations",
        status="paid",
        vendor_name="OpenCloud",
    )

    assert expense.currency == "USD"
    assert expense.status == "paid"
    assert calls == [
        {
            "tenant_id": "tenant-1",
            "expense_id": expense.id,
            "title": "Cloud hosting",
            "expense_date": date(2026, 4, 14),
            "currency": "USD",
            "amount": Decimal("199.00"),
            "vendor_name": "OpenCloud",
        }
    ]


@pytest.mark.asyncio
async def test_update_expense_to_paid_posts_accounting_once(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeExpensesSession()
    calls: list[dict[str, Any]] = []

    async def _record_posting(*args: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("app.expenses.service.sync_expense_accounting_entries", _record_posting)

    expense = await update_expense(
        session,
        tenant_id="tenant-1",
        expense_id="expense-1",
        status="paid",
    )

    assert expense.status == "paid"
    assert len(calls) == 1
    assert calls[0]["expense_id"] == "expense-1"


@pytest.mark.asyncio
async def test_paid_expense_cannot_be_edited() -> None:
    with pytest.raises(ValueError, match="Paid expenses are locked"):
        await update_expense(
            FakeExpensesSession(),
            tenant_id="tenant-1",
            expense_id="expense-2",
            title="Changed title",
        )


def test_convert_tenant_secondary_currency_amount_is_explicit_and_reversible() -> None:
    as_of = datetime(2026, 4, 14, 9, 30, tzinfo=UTC)

    sek_to_eur = convert_tenant_secondary_currency_amount(
        amount=Decimal("100.00"),
        amount_currency="SEK",
        default_currency="SEK",
        secondary_currency="EUR",
        secondary_currency_rate=Decimal("0.091500"),
        rate_source="operator_manual",
        rate_as_of=as_of,
    )
    eur_to_sek = convert_tenant_secondary_currency_amount(
        amount=Decimal("9.15"),
        amount_currency="EUR",
        default_currency="SEK",
        secondary_currency="EUR",
        secondary_currency_rate=Decimal("0.091500"),
        rate_source="operator_manual",
        rate_as_of=as_of,
    )

    assert sek_to_eur is not None
    assert sek_to_eur.converted_amount == Decimal("9.15")
    assert sek_to_eur.converted_currency == "EUR"
    assert sek_to_eur.rate_source == "operator_manual"
    assert sek_to_eur.rate_as_of == as_of

    assert eur_to_sek is not None
    assert eur_to_sek.converted_amount == Decimal("100.00")
    assert eur_to_sek.converted_currency == "SEK"

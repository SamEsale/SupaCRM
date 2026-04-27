from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.accounting.schemas import AccountingAccountType
from app.accounting.service import (
    ALLOWED_ACCOUNT_TYPES,
    INVOICE_ISSUED_EVENT,
    JournalEntryLineInput,
    create_account,
    create_journal_entry,
    get_financial_statements_report,
    list_accounts,
    list_journal_entries,
    sync_invoice_accounting_entries,
)


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
        first_row: dict[str, Any] | None = None,
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar
        self._first_row = first_row

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise AssertionError("Expected scalar result")
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def first(self) -> Any:
        if self._first_row is not None:
            return self._first_row
        return self._rows[0] if self._rows else None


class FakeAccountingSession:
    def __init__(self) -> None:
        self.accounts: dict[str, dict[str, Any]] = {}
        self.journal_entries: dict[str, dict[str, Any]] = {}
        self.journal_entry_lines: dict[str, dict[str, Any]] = {}
        self.invoices = {
            "invoice-open": {
                "id": "invoice-open",
                "tenant_id": "tenant-1",
                "number": "INV-1001",
                "company_id": "company-1",
                "status": "issued",
                "due_date": date(2026, 4, 30),
                "currency": "USD",
                "total_amount": Decimal("300.00"),
                "created_at": datetime(2026, 4, 10, tzinfo=timezone.utc),
            },
            "invoice-paid": {
                "id": "invoice-paid",
                "tenant_id": "tenant-1",
                "number": "INV-1002",
                "company_id": "company-1",
                "status": "paid",
                "due_date": date(2026, 4, 22),
                "currency": "USD",
                "total_amount": Decimal("100.00"),
                "created_at": datetime(2026, 4, 11, tzinfo=timezone.utc),
            },
            "invoice-other-tenant": {
                "id": "invoice-other-tenant",
                "tenant_id": "tenant-2",
                "number": "INV-9001",
                "company_id": "company-x",
                "status": "issued",
                "due_date": date(2026, 4, 28),
                "currency": "EUR",
                "total_amount": Decimal("999.00"),
                "created_at": datetime(2026, 4, 11, tzinfo=timezone.utc),
            },
        }
        self.invoice_payments = {
            "payment-paid": {
                "id": "payment-paid",
                "tenant_id": "tenant-1",
                "invoice_id": "invoice-paid",
                "amount": Decimal("100.00"),
                "status": "completed",
            }
        }

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "insert into public.accounting_accounts" in sql and "on conflict" in sql:
            return self._upsert_default_account(payload)

        if "insert into public.accounting_accounts" in sql:
            return self._insert_account(payload)

        if (
            "select 1 from public.accounting_accounts" in sql
            and "id = cast(:account_id as varchar)" in sql
        ):
            account = self.accounts.get(str(payload["account_id"]))
            if account and account["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if (
            "select 1 from public.accounting_accounts" in sql
            and "code = cast(:code as varchar)" in sql
        ):
            existing = self._find_account_by_code(
                tenant_id=str(payload["tenant_id"]),
                code=str(payload["code"]),
            )
            return _FakeResult(scalar=1 if existing else None)

        if (
            "from public.accounting_accounts where tenant_id = cast(:tenant_id as varchar) and system_key = cast(:system_key as varchar)"
            in sql
        ):
            account = self._find_account_by_system_key(
                tenant_id=str(payload["tenant_id"]),
                system_key=str(payload["system_key"]),
            )
            return _FakeResult(rows=[dict(account)] if account else [])

        if (
            "from public.accounting_accounts where tenant_id = cast(:tenant_id as varchar) order by code asc, name asc"
            in sql
        ):
            tenant_accounts = [
                dict(account)
                for account in self.accounts.values()
                if account["tenant_id"] == str(payload["tenant_id"])
            ]
            tenant_accounts.sort(key=lambda item: (item["code"], item["name"]))
            return _FakeResult(rows=tenant_accounts)

        if (
            "select 1 from public.journal_entries" in sql
            and "source_type = cast(:source_type as varchar)" in sql
        ):
            exists = self._find_journal_entry_by_source(
                tenant_id=str(payload["tenant_id"]),
                source_type=str(payload["source_type"]),
                source_id=str(payload["source_id"]),
                source_event=str(payload["source_event"]),
            )
            return _FakeResult(scalar=1 if exists else None)

        if "insert into public.journal_entries" in sql:
            now = datetime.now(timezone.utc)
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "entry_date": payload["entry_date"],
                "memo": str(payload["memo"]),
                "source_type": payload.get("source_type"),
                "source_id": payload.get("source_id"),
                "source_event": payload.get("source_event"),
                "currency": str(payload["currency"]),
                "created_at": now,
            }
            self.journal_entries[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "insert into public.journal_entry_lines" in sql:
            now = datetime.now(timezone.utc)
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "journal_entry_id": str(payload["journal_entry_id"]),
                "account_id": str(payload["account_id"]),
                "line_order": int(payload["line_order"]),
                "description": payload.get("description"),
                "debit_amount": Decimal(str(payload["debit_amount"])),
                "credit_amount": Decimal(str(payload["credit_amount"])),
                "created_at": now,
            }
            self.journal_entry_lines[row["id"]] = row
            return _FakeResult(rows=[])

        if (
            "select id from public.journal_entries" in sql
            and "source_event = cast(:source_event as varchar)" in sql
        ):
            entry = self._find_journal_entry_by_source(
                tenant_id=str(payload["tenant_id"]),
                source_type=str(payload["source_type"]),
                source_id=str(payload["source_id"]),
                source_event=str(payload["source_event"]),
            )
            return _FakeResult(rows=[{"id": entry["id"]}] if entry else [])

        if (
            "from public.journal_entries where tenant_id = cast(:tenant_id as varchar) and id = cast(:journal_entry_id as varchar)"
            in sql
        ):
            entry = self.journal_entries.get(str(payload["journal_entry_id"]))
            if not entry or entry["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(entry)])

        if (
            "from public.journal_entry_lines jel join public.accounting_accounts aa"
            in sql
        ):
            journal_entry_ids = payload.get("journal_entry_ids", [])
            rows: list[dict[str, Any]] = []
            for line in sorted(
                self.journal_entry_lines.values(),
                key=lambda item: (
                    item["journal_entry_id"],
                    item["line_order"],
                    item["id"],
                ),
            ):
                if (
                    line["tenant_id"] != str(payload["tenant_id"])
                    or line["journal_entry_id"] not in journal_entry_ids
                ):
                    continue
                account = self.accounts[line["account_id"]]
                rows.append(
                    {
                        "line_id": line["id"],
                        "tenant_id": line["tenant_id"],
                        "journal_entry_id": line["journal_entry_id"],
                        "account_id": line["account_id"],
                        "account_code": account["code"],
                        "account_name": account["name"],
                        "account_type": account["account_type"],
                        "line_order": line["line_order"],
                        "line_description": line["description"],
                        "debit_amount": line["debit_amount"],
                        "credit_amount": line["credit_amount"],
                        "line_created_at": line["created_at"],
                    }
                )
            return _FakeResult(rows=rows)

        if "select count(*) from public.journal_entries" in sql:
            entries = self._filter_entries(payload)
            return _FakeResult(scalar=len(entries))

        if (
            "from public.journal_entries where tenant_id = cast(:tenant_id as varchar)"
            in sql
            and "order by entry_date desc" in sql
        ):
            rows = [dict(entry) for entry in self._filter_entries(payload)]
            rows.sort(
                key=lambda item: (item["entry_date"], item["created_at"], item["id"]),
                reverse=True,
            )
            offset = int(payload.get("offset", 0))
            limit = int(payload.get("limit", len(rows)))
            return _FakeResult(rows=rows[offset : offset + limit])

        if (
            "select aa.id as account_id" in sql
            and "left join public.journal_entry_lines jel" in sql
        ):
            tenant_id = str(payload["tenant_id"])
            rows: list[dict[str, Any]] = []
            for account in sorted(
                [
                    item
                    for item in self.accounts.values()
                    if item["tenant_id"] == tenant_id
                ],
                key=lambda item: item["code"],
            ):
                matching_lines = [
                    line
                    for line in self.journal_entry_lines.values()
                    if line["tenant_id"] == tenant_id
                    and line["account_id"] == account["id"]
                ]
                if not matching_lines:
                    rows.append(
                        {
                            "account_id": account["id"],
                            "code": account["code"],
                            "name": account["name"],
                            "account_type": account["account_type"],
                            "currency": None,
                            "total_debit": Decimal("0.00"),
                            "total_credit": Decimal("0.00"),
                        }
                    )
                    continue
                by_currency: dict[str, dict[str, Any]] = {}
                for line in matching_lines:
                    entry = self.journal_entries[line["journal_entry_id"]]
                    bucket = by_currency.setdefault(
                        entry["currency"],
                        {
                            "account_id": account["id"],
                            "code": account["code"],
                            "name": account["name"],
                            "account_type": account["account_type"],
                            "currency": entry["currency"],
                            "total_debit": Decimal("0.00"),
                            "total_credit": Decimal("0.00"),
                        },
                    )
                    bucket["total_debit"] += line["debit_amount"]
                    bucket["total_credit"] += line["credit_amount"]
                rows.extend(by_currency.values())
            return _FakeResult(rows=rows)

        if "from public.invoices i left join public.invoice_payments ip" in sql:
            rows = [
                {
                    "id": invoice["id"],
                    "number": invoice["number"],
                    "company_id": invoice["company_id"],
                    "status": invoice["status"],
                    "due_date": invoice["due_date"],
                    "currency": invoice["currency"],
                    "total_amount": invoice["total_amount"],
                    "paid_amount": sum(
                        payment["amount"]
                        for payment in self.invoice_payments.values()
                        if payment["tenant_id"] == str(payload["tenant_id"])
                        and payment["invoice_id"] == invoice["id"]
                        and payment["status"] == "completed"
                    ),
                }
                for invoice in self.invoices.values()
                if invoice["tenant_id"] == str(payload["tenant_id"])
                and invoice["status"] in {"issued", "overdue", "paid"}
            ]
            return _FakeResult(rows=rows)

        raise AssertionError(f"Unhandled SQL in FakeAccountingSession: {sql}")

    def _upsert_default_account(self, payload: dict[str, Any]) -> _FakeResult:
        tenant_id = str(payload["tenant_id"])
        code = str(payload["code"])
        now = datetime.now(timezone.utc)
        existing = self._find_account_by_code(tenant_id=tenant_id, code=code)
        if existing:
            existing["name"] = str(payload["name"])
            existing["account_type"] = str(payload["account_type"])
            existing["system_key"] = existing.get("system_key") or payload.get(
                "system_key"
            )
            existing["is_active"] = True
            existing["updated_at"] = now
            return _FakeResult(rows=[])

        row = {
            "id": str(payload["id"]),
            "tenant_id": tenant_id,
            "code": code,
            "name": str(payload["name"]),
            "account_type": str(payload["account_type"]),
            "system_key": payload.get("system_key"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        self.accounts[row["id"]] = row
        return _FakeResult(rows=[])

    def _insert_account(self, payload: dict[str, Any]) -> _FakeResult:
        now = datetime.now(timezone.utc)
        row = {
            "id": str(payload["id"]),
            "tenant_id": str(payload["tenant_id"]),
            "code": str(payload["code"]),
            "name": str(payload["name"]),
            "account_type": str(payload["account_type"]),
            "system_key": payload.get("system_key"),
            "is_active": bool(payload["is_active"]),
            "created_at": now,
            "updated_at": now,
        }
        self.accounts[row["id"]] = row
        return _FakeResult(rows=[dict(row)])

    def _find_account_by_code(
        self, *, tenant_id: str, code: str
    ) -> dict[str, Any] | None:
        for account in self.accounts.values():
            if account["tenant_id"] == tenant_id and account["code"] == code:
                return account
        return None

    def _find_account_by_system_key(
        self, *, tenant_id: str, system_key: str
    ) -> dict[str, Any] | None:
        for account in self.accounts.values():
            if (
                account["tenant_id"] == tenant_id
                and account.get("system_key") == system_key
            ):
                return account
        return None

    def _find_journal_entry_by_source(
        self,
        *,
        tenant_id: str,
        source_type: str,
        source_id: str,
        source_event: str,
    ) -> dict[str, Any] | None:
        for entry in self.journal_entries.values():
            if (
                entry["tenant_id"] == tenant_id
                and entry.get("source_type") == source_type
                and entry.get("source_id") == source_id
                and entry.get("source_event") == source_event
            ):
                return entry
        return None

    def _filter_entries(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        tenant_id = str(payload["tenant_id"])
        rows = [
            entry
            for entry in self.journal_entries.values()
            if entry["tenant_id"] == tenant_id
        ]
        if payload.get("source_type") is not None:
            rows = [
                entry
                for entry in rows
                if entry.get("source_type") == str(payload["source_type"])
            ]
        if payload.get("source_id") is not None:
            rows = [
                entry
                for entry in rows
                if entry.get("source_id") == str(payload["source_id"])
            ]
        if payload.get("source_event") is not None:
            rows = [
                entry
                for entry in rows
                if entry.get("source_event") == str(payload["source_event"])
            ]
        return rows


@pytest.fixture
def session() -> FakeAccountingSession:
    return FakeAccountingSession()


def test_account_type_contract_matches_schema() -> None:
    assert set(ALLOWED_ACCOUNT_TYPES) == set(AccountingAccountType.__args__)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_create_account_and_list_accounts_include_defaults(
    session: FakeAccountingSession,
) -> None:
    before = await list_accounts(session, tenant_id="tenant-1")
    assert [item.system_key for item in before.items[:3]] == [
        "cash",
        "accounts_receivable",
        "sales_revenue",
    ]

    created = await create_account(
        session,
        tenant_id="tenant-1",
        code="6100",
        name="Office Software",
        account_type="expense",
    )

    after = await list_accounts(session, tenant_id="tenant-1")
    assert created.code == "6100"
    assert created.account_type == "expense"
    assert after.total == 5


@pytest.mark.asyncio
async def test_create_journal_entry_enforces_balanced_lines(
    session: FakeAccountingSession,
) -> None:
    accounts = await list_accounts(session, tenant_id="tenant-1")
    cash_account = next(item for item in accounts.items if item.system_key == "cash")
    revenue_account = next(
        item for item in accounts.items if item.system_key == "sales_revenue"
    )

    with pytest.raises(ValueError, match="Journal entries must be balanced"):
        await create_journal_entry(
            session,
            tenant_id="tenant-1",
            entry_date=date(2026, 4, 13),
            memo="Broken entry",
            currency="USD",
            lines=[
                JournalEntryLineInput(
                    account_id=cash_account.id,
                    debit_amount=Decimal("100.00"),
                    credit_amount=Decimal("0.00"),
                ),
                JournalEntryLineInput(
                    account_id=revenue_account.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("90.00"),
                ),
            ],
        )


@pytest.mark.asyncio
async def test_sync_invoice_accounting_entries_posts_invoice_events_once(
    session: FakeAccountingSession,
) -> None:
    await sync_invoice_accounting_entries(
        session,
        tenant_id="tenant-1",
        invoice_id="invoice-open",
        invoice_number="INV-1001",
        issue_date=date(2026, 4, 10),
        currency="USD",
        total_amount=Decimal("300.00"),
        status="issued",
    )
    await sync_invoice_accounting_entries(
        session,
        tenant_id="tenant-1",
        invoice_id="invoice-open",
        invoice_number="INV-1001",
        issue_date=date(2026, 4, 10),
        currency="USD",
        total_amount=Decimal("300.00"),
        status="issued",
    )
    await sync_invoice_accounting_entries(
        session,
        tenant_id="tenant-1",
        invoice_id="invoice-paid",
        invoice_number="INV-1002",
        issue_date=date(2026, 4, 11),
        currency="USD",
        total_amount=Decimal("100.00"),
        status="paid",
    )

    entries = await list_journal_entries(
        session,
        tenant_id="tenant-1",
        source_type="invoice",
        limit=20,
        offset=0,
    )
    source_events = {(item.source_id, item.source_event) for item in entries.items}

    assert entries.total == 2
    assert ("invoice-open", INVOICE_ISSUED_EVENT) in source_events
    assert ("invoice-paid", INVOICE_ISSUED_EVENT) in source_events


@pytest.mark.asyncio
async def test_financial_statements_report_is_tenant_scoped(
    session: FakeAccountingSession,
) -> None:
    await sync_invoice_accounting_entries(
        session,
        tenant_id="tenant-1",
        invoice_id="invoice-open",
        invoice_number="INV-1001",
        issue_date=date(2026, 4, 10),
        currency="USD",
        total_amount=Decimal("300.00"),
        status="issued",
    )
    await sync_invoice_accounting_entries(
        session,
        tenant_id="tenant-1",
        invoice_id="invoice-paid",
        invoice_number="INV-1002",
        issue_date=date(2026, 4, 11),
        currency="USD",
        total_amount=Decimal("100.00"),
        status="paid",
    )
    await sync_invoice_accounting_entries(
        session,
        tenant_id="tenant-2",
        invoice_id="invoice-other-tenant",
        invoice_number="INV-9001",
        issue_date=date(2026, 4, 11),
        currency="EUR",
        total_amount=Decimal("999.00"),
        status="issued",
    )

    report = await get_financial_statements_report(session, tenant_id="tenant-1")

    assert report.profit_and_loss.total_revenue == Decimal("400.00")
    assert report.profit_and_loss.net_income == Decimal("400.00")
    assert report.balance_sheet.total_assets == Decimal("400.00")
    assert report.balance_sheet.total_liabilities == Decimal("0.00")
    assert report.balance_sheet.total_equity == Decimal("400.00")
    assert report.receivables.open_receivables_amount == Decimal("300.00")
    assert report.receivables.issued_invoice_count == 1
    assert report.receivables.paid_invoice_count == 1
    assert report.profit_and_loss.currencies == ["USD"]
    assert report.vat_supported is False

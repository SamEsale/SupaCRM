from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


ALLOWED_ACCOUNT_TYPES: tuple[str, ...] = (
    "asset",
    "liability",
    "equity",
    "revenue",
    "expense",
)

DEFAULT_SYSTEM_ACCOUNTS: tuple[tuple[str, str, str, str], ...] = (
    ("cash", "1000", "Cash", "asset"),
    ("accounts_receivable", "1100", "Accounts Receivable", "asset"),
    ("sales_revenue", "4000", "Sales Revenue", "revenue"),
    ("operating_expenses", "5000", "Operating Expenses", "expense"),
)

INVOICE_ISSUED_EVENT = "invoice_issued"
INVOICE_PAID_EVENT = "invoice_paid"
INVOICE_CANCELLED_EVENT = "invoice_cancelled"
PAYMENT_COMPLETED_EVENT = "payment_completed"
EXPENSE_PAID_EVENT = "expense_paid"


@dataclass(slots=True)
class AccountingAccountDetails:
    id: str
    tenant_id: str
    code: str
    name: str
    account_type: str
    system_key: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class AccountingAccountListResult:
    items: list[AccountingAccountDetails]
    total: int


@dataclass(slots=True)
class JournalEntryLineDetails:
    id: str
    tenant_id: str
    journal_entry_id: str
    account_id: str
    account_code: str
    account_name: str
    account_type: str
    line_order: int
    description: str | None
    debit_amount: Decimal
    credit_amount: Decimal
    created_at: datetime


@dataclass(slots=True)
class JournalEntryDetails:
    id: str
    tenant_id: str
    entry_date: date
    memo: str
    source_type: str | None
    source_id: str | None
    source_event: str | None
    currency: str
    total_debit: Decimal
    total_credit: Decimal
    created_at: datetime
    lines: list[JournalEntryLineDetails]


@dataclass(slots=True)
class JournalEntryListResult:
    items: list[JournalEntryDetails]
    total: int


@dataclass(slots=True)
class JournalEntryLineInput:
    account_id: str
    debit_amount: Decimal
    credit_amount: Decimal
    description: str | None = None


@dataclass(slots=True)
class FinancialStatementLine:
    account_id: str
    code: str
    name: str
    account_type: str
    total_amount: Decimal
    currencies: list[str]


@dataclass(slots=True)
class ProfitAndLossStatement:
    revenue_lines: list[FinancialStatementLine]
    expense_lines: list[FinancialStatementLine]
    total_revenue: Decimal
    total_expenses: Decimal
    net_income: Decimal
    currencies: list[str]


@dataclass(slots=True)
class BalanceSheetStatement:
    asset_lines: list[FinancialStatementLine]
    liability_lines: list[FinancialStatementLine]
    equity_lines: list[FinancialStatementLine]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    currencies: list[str]


@dataclass(slots=True)
class ReceivablesInvoiceItem:
    invoice_id: str
    invoice_number: str
    company_id: str
    status: str
    due_date: date
    currency: str
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal


@dataclass(slots=True)
class ReceivablesSummary:
    open_receivables_amount: Decimal
    issued_invoice_count: int
    overdue_invoice_count: int
    paid_invoice_count: int
    currencies: list[str]
    items: list[ReceivablesInvoiceItem]


@dataclass(slots=True)
class FinancialStatementsReport:
    profit_and_loss: ProfitAndLossStatement
    balance_sheet: BalanceSheetStatement
    receivables: ReceivablesSummary
    vat_supported: bool
    vat_note: str
    generated_at: datetime


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_account_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_ACCOUNT_TYPES:
        raise ValueError(
            "Invalid account type. Allowed values: " + ", ".join(ALLOWED_ACCOUNT_TYPES)
        )
    return normalized


def _normalize_currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("Currency must be a valid ISO 4217 uppercase 3-letter code")
    return normalized


def _normalize_decimal(value: Decimal | str | int | float) -> Decimal:
    if isinstance(value, Decimal):
        normalized = value
    else:
        try:
            normalized = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Amounts must be valid decimal values") from exc
    if normalized < 0:
        raise ValueError("Amounts must be zero or greater")
    return normalized.quantize(Decimal("0.01"))


def _account_from_row(row: dict[str, object]) -> AccountingAccountDetails:
    return AccountingAccountDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        code=str(row["code"]),
        name=str(row["name"]),
        account_type=str(row["account_type"]),
        system_key=row["system_key"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _line_from_row(row: dict[str, object]) -> JournalEntryLineDetails:
    return JournalEntryLineDetails(
        id=str(row["line_id"]),
        tenant_id=str(row["tenant_id"]),
        journal_entry_id=str(row["journal_entry_id"]),
        account_id=str(row["account_id"]),
        account_code=str(row["account_code"]),
        account_name=str(row["account_name"]),
        account_type=str(row["account_type"]),
        line_order=int(row["line_order"]),
        description=row["line_description"],
        debit_amount=Decimal(str(row["debit_amount"])),
        credit_amount=Decimal(str(row["credit_amount"])),
        created_at=row["line_created_at"],
    )


async def _account_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    account_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.accounting_accounts
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:account_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "account_id": account_id},
    )
    return result.scalar_one_or_none() == 1


async def _account_code_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    code: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.accounting_accounts
            where tenant_id = cast(:tenant_id as varchar)
              and code = cast(:code as varchar)
            """
        ),
        {"tenant_id": tenant_id, "code": code},
    )
    return result.scalar_one_or_none() == 1


async def ensure_default_accounts(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> None:
    for system_key, code, name, account_type in DEFAULT_SYSTEM_ACCOUNTS:
        await session.execute(
            text(
                """
                insert into public.accounting_accounts (
                    id,
                    tenant_id,
                    code,
                    name,
                    account_type,
                    system_key,
                    is_active
                )
                values (
                    cast(:id as varchar),
                    cast(:tenant_id as varchar),
                    cast(:code as varchar),
                    cast(:name as varchar),
                    cast(:account_type as varchar),
                    cast(:system_key as varchar),
                    true
                )
                on conflict (tenant_id, code) do update
                set name = excluded.name,
                    account_type = excluded.account_type,
                    system_key = coalesce(public.accounting_accounts.system_key, excluded.system_key),
                    is_active = true,
                    updated_at = now()
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "code": code,
                "name": name,
                "account_type": account_type,
                "system_key": system_key,
            },
        )


async def list_accounts(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> AccountingAccountListResult:
    await ensure_default_accounts(session, tenant_id=tenant_id)
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                code,
                name,
                account_type,
                system_key,
                is_active,
                created_at,
                updated_at
            from public.accounting_accounts
            where tenant_id = cast(:tenant_id as varchar)
            order by code asc, name asc
            """
        ),
        {"tenant_id": tenant_id},
    )
    rows = list(result.mappings())
    return AccountingAccountListResult(
        items=[_account_from_row(row) for row in rows],
        total=len(rows),
    )


async def create_account(
    session: AsyncSession,
    *,
    tenant_id: str,
    code: str,
    name: str,
    account_type: str,
    is_active: bool = True,
) -> AccountingAccountDetails:
    await ensure_default_accounts(session, tenant_id=tenant_id)

    normalized_code = code.strip()
    normalized_name = name.strip()
    normalized_type = _normalize_account_type(account_type)

    if not normalized_code:
        raise ValueError("Account code is required")
    if not normalized_name:
        raise ValueError("Account name is required")
    if await _account_code_exists_for_tenant(session, tenant_id=tenant_id, code=normalized_code):
        raise ValueError(f"Account code already exists for tenant {tenant_id}: {normalized_code}")

    result = await session.execute(
        text(
            """
            insert into public.accounting_accounts (
                id,
                tenant_id,
                code,
                name,
                account_type,
                system_key,
                is_active
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:code as varchar),
                cast(:name as varchar),
                cast(:account_type as varchar),
                null,
                :is_active
            )
            returning
                id,
                tenant_id,
                code,
                name,
                account_type,
                system_key,
                is_active,
                created_at,
                updated_at
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "code": normalized_code,
            "name": normalized_name,
            "account_type": normalized_type,
            "is_active": is_active,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create account")
    return _account_from_row(row)


async def _journal_entry_exists_for_source(
    session: AsyncSession,
    *,
    tenant_id: str,
    source_type: str,
    source_id: str,
    source_event: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.journal_entries
            where tenant_id = cast(:tenant_id as varchar)
              and source_type = cast(:source_type as varchar)
              and source_id = cast(:source_id as varchar)
              and source_event = cast(:source_event as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "source_type": source_type,
            "source_id": source_id,
            "source_event": source_event,
        },
    )
    return result.scalar_one_or_none() == 1


async def _get_account_by_system_key(
    session: AsyncSession,
    *,
    tenant_id: str,
    system_key: str,
) -> AccountingAccountDetails:
    await ensure_default_accounts(session, tenant_id=tenant_id)
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                code,
                name,
                account_type,
                system_key,
                is_active,
                created_at,
                updated_at
            from public.accounting_accounts
            where tenant_id = cast(:tenant_id as varchar)
              and system_key = cast(:system_key as varchar)
            limit 1
            """
        ),
        {"tenant_id": tenant_id, "system_key": system_key},
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(f"Default accounting account is missing for tenant {tenant_id}: {system_key}")
    return _account_from_row(row)


async def create_journal_entry(
    session: AsyncSession,
    *,
    tenant_id: str,
    entry_date: date,
    memo: str,
    currency: str,
    lines: list[JournalEntryLineInput],
    source_type: str | None = None,
    source_id: str | None = None,
    source_event: str | None = None,
) -> JournalEntryDetails:
    normalized_memo = memo.strip()
    normalized_currency = _normalize_currency(currency)
    if not normalized_memo:
        raise ValueError("Journal entry memo is required")
    if len(lines) < 2:
        raise ValueError("Journal entries require at least two lines")

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for line in lines:
        if not await _account_exists_for_tenant(session, tenant_id=tenant_id, account_id=line.account_id):
            raise ValueError(f"Accounting account does not exist: {line.account_id}")

        debit_amount = _normalize_decimal(line.debit_amount)
        credit_amount = _normalize_decimal(line.credit_amount)

        if debit_amount == Decimal("0.00") and credit_amount == Decimal("0.00"):
            raise ValueError("Journal entry lines must contain a debit or credit amount")
        if debit_amount > Decimal("0.00") and credit_amount > Decimal("0.00"):
            raise ValueError("Journal entry lines cannot contain both debit and credit amounts")

        total_debit += debit_amount
        total_credit += credit_amount

    if total_debit != total_credit:
        raise ValueError("Journal entries must be balanced")

    if source_type and source_id and source_event and await _journal_entry_exists_for_source(
        session,
        tenant_id=tenant_id,
        source_type=source_type,
        source_id=source_id,
        source_event=source_event,
    ):
        return await get_journal_entry_by_source(
            session,
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id,
            source_event=source_event,
        )

    journal_entry_id = str(uuid.uuid4())
    entry_result = await session.execute(
        text(
            """
            insert into public.journal_entries (
                id,
                tenant_id,
                entry_date,
                memo,
                source_type,
                source_id,
                source_event,
                currency
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                :entry_date,
                :memo,
                cast(:source_type as varchar),
                cast(:source_id as varchar),
                cast(:source_event as varchar),
                cast(:currency as varchar)
            )
            returning
                id,
                tenant_id,
                entry_date,
                memo,
                source_type,
                source_id,
                source_event,
                currency,
                created_at
            """
        ),
        {
            "id": journal_entry_id,
            "tenant_id": tenant_id,
            "entry_date": entry_date,
            "memo": normalized_memo,
            "source_type": _clean_optional(source_type),
            "source_id": _clean_optional(source_id),
            "source_event": _clean_optional(source_event),
            "currency": normalized_currency,
        },
    )
    entry_row = entry_result.mappings().first()
    if not entry_row:
        raise ValueError("Failed to create journal entry")

    for index, line in enumerate(lines, start=1):
        await session.execute(
            text(
                """
                insert into public.journal_entry_lines (
                    id,
                    tenant_id,
                    journal_entry_id,
                    account_id,
                    line_order,
                    description,
                    debit_amount,
                    credit_amount
                )
                values (
                    cast(:id as varchar),
                    cast(:tenant_id as varchar),
                    cast(:journal_entry_id as varchar),
                    cast(:account_id as varchar),
                    :line_order,
                    :description,
                    :debit_amount,
                    :credit_amount
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "journal_entry_id": journal_entry_id,
                "account_id": line.account_id,
                "line_order": index,
                "description": _clean_optional(line.description),
                "debit_amount": _normalize_decimal(line.debit_amount),
                "credit_amount": _normalize_decimal(line.credit_amount),
            },
        )

    return await get_journal_entry_by_id(session, tenant_id=tenant_id, journal_entry_id=journal_entry_id)


async def _load_journal_entry_lines(
    session: AsyncSession,
    *,
    tenant_id: str,
    journal_entry_ids: list[str],
) -> dict[str, list[JournalEntryLineDetails]]:
    if not journal_entry_ids:
        return {}

    result = await session.execute(
        text(
            """
            select
                jel.id as line_id,
                jel.tenant_id,
                jel.journal_entry_id,
                jel.account_id,
                aa.code as account_code,
                aa.name as account_name,
                aa.account_type,
                jel.line_order,
                jel.description as line_description,
                jel.debit_amount,
                jel.credit_amount,
                jel.created_at as line_created_at
            from public.journal_entry_lines jel
            join public.accounting_accounts aa
              on aa.id = jel.account_id
             and aa.tenant_id = jel.tenant_id
            where jel.tenant_id = cast(:tenant_id as varchar)
              and jel.journal_entry_id = any(:journal_entry_ids)
            order by jel.journal_entry_id asc, jel.line_order asc, jel.id asc
            """
        ),
        {"tenant_id": tenant_id, "journal_entry_ids": journal_entry_ids},
    )
    grouped: dict[str, list[JournalEntryLineDetails]] = {}
    for row in result.mappings():
        line = _line_from_row(row)
        grouped.setdefault(line.journal_entry_id, []).append(line)
    return grouped


async def get_journal_entry_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    journal_entry_id: str,
) -> JournalEntryDetails:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                entry_date,
                memo,
                source_type,
                source_id,
                source_event,
                currency,
                created_at
            from public.journal_entries
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:journal_entry_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "journal_entry_id": journal_entry_id},
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(f"Journal entry does not exist: {journal_entry_id}")

    lines_by_entry = await _load_journal_entry_lines(
        session,
        tenant_id=tenant_id,
        journal_entry_ids=[journal_entry_id],
    )
    lines = lines_by_entry.get(journal_entry_id, [])
    total_debit = sum((line.debit_amount for line in lines), Decimal("0.00"))
    total_credit = sum((line.credit_amount for line in lines), Decimal("0.00"))
    return JournalEntryDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        entry_date=row["entry_date"],
        memo=str(row["memo"]),
        source_type=row["source_type"],
        source_id=row["source_id"],
        source_event=row["source_event"],
        currency=str(row["currency"]),
        total_debit=total_debit,
        total_credit=total_credit,
        created_at=row["created_at"],
        lines=lines,
    )


async def get_journal_entry_by_source(
    session: AsyncSession,
    *,
    tenant_id: str,
    source_type: str,
    source_id: str,
    source_event: str,
) -> JournalEntryDetails:
    result = await session.execute(
        text(
            """
            select id
            from public.journal_entries
            where tenant_id = cast(:tenant_id as varchar)
              and source_type = cast(:source_type as varchar)
              and source_id = cast(:source_id as varchar)
              and source_event = cast(:source_event as varchar)
            limit 1
            """
        ),
        {
            "tenant_id": tenant_id,
            "source_type": source_type,
            "source_id": source_id,
            "source_event": source_event,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(
            f"Journal entry does not exist for source {source_type}:{source_id}:{source_event}"
        )
    return await get_journal_entry_by_id(
        session,
        tenant_id=tenant_id,
        journal_entry_id=str(row["id"]),
    )


async def list_journal_entries(
    session: AsyncSession,
    *,
    tenant_id: str,
    source_type: str | None = None,
    source_id: str | None = None,
    source_event: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> JournalEntryListResult:
    count_sql = """
        select count(*)
        from public.journal_entries
        where tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            id,
            tenant_id,
            entry_date,
            memo,
            source_type,
            source_id,
            source_event,
            currency,
            created_at
        from public.journal_entries
        where tenant_id = cast(:tenant_id as varchar)
    """
    params: dict[str, object] = {
        "tenant_id": tenant_id,
        "limit": limit,
        "offset": offset,
    }
    if source_type:
        count_sql += " and source_type = cast(:source_type as varchar) "
        list_sql += " and source_type = cast(:source_type as varchar) "
        params["source_type"] = source_type
    if source_id:
        count_sql += " and source_id = cast(:source_id as varchar) "
        list_sql += " and source_id = cast(:source_id as varchar) "
        params["source_id"] = source_id
    if source_event:
        count_sql += " and source_event = cast(:source_event as varchar) "
        list_sql += " and source_event = cast(:source_event as varchar) "
        params["source_event"] = source_event
    list_sql += """
        order by entry_date desc, created_at desc, id desc
        limit :limit
        offset :offset
    """

    total = int((await session.execute(text(count_sql), params)).scalar_one())
    rows = list((await session.execute(text(list_sql), params)).mappings())
    entry_ids = [str(row["id"]) for row in rows]
    lines_by_entry = await _load_journal_entry_lines(
        session,
        tenant_id=tenant_id,
        journal_entry_ids=entry_ids,
    )

    items: list[JournalEntryDetails] = []
    for row in rows:
        journal_entry_id = str(row["id"])
        lines = lines_by_entry.get(journal_entry_id, [])
        items.append(
            JournalEntryDetails(
                id=journal_entry_id,
                tenant_id=str(row["tenant_id"]),
                entry_date=row["entry_date"],
                memo=str(row["memo"]),
                source_type=row["source_type"],
                source_id=row["source_id"],
                source_event=row["source_event"],
                currency=str(row["currency"]),
                total_debit=sum((line.debit_amount for line in lines), Decimal("0.00")),
                total_credit=sum((line.credit_amount for line in lines), Decimal("0.00")),
                created_at=row["created_at"],
                lines=lines,
            )
        )
    return JournalEntryListResult(items=items, total=total)


async def sync_invoice_accounting_entries(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
    invoice_number: str,
    issue_date: date,
    currency: str,
    total_amount: Decimal,
    status: str,
    memo: str | None = None,
) -> None:
    await ensure_default_accounts(session, tenant_id=tenant_id)

    accounts_receivable = await _get_account_by_system_key(
        session,
        tenant_id=tenant_id,
        system_key="accounts_receivable",
    )
    cash_account = await _get_account_by_system_key(
        session,
        tenant_id=tenant_id,
        system_key="cash",
    )
    sales_revenue = await _get_account_by_system_key(
        session,
        tenant_id=tenant_id,
        system_key="sales_revenue",
    )

    normalized_status = status.strip().lower()
    normalized_currency = _normalize_currency(currency)
    normalized_amount = _normalize_decimal(total_amount)
    entry_memo = memo or f"Invoice {invoice_number}"

    if normalized_status in {"issued", "overdue", "paid"} and not await _journal_entry_exists_for_source(
        session,
        tenant_id=tenant_id,
        source_type="invoice",
        source_id=invoice_id,
        source_event=INVOICE_ISSUED_EVENT,
    ):
        await create_journal_entry(
            session,
            tenant_id=tenant_id,
            entry_date=issue_date,
            memo=f"{entry_memo} issued",
            currency=normalized_currency,
            source_type="invoice",
            source_id=invoice_id,
            source_event=INVOICE_ISSUED_EVENT,
            lines=[
                JournalEntryLineInput(
                    account_id=accounts_receivable.id,
                    debit_amount=normalized_amount,
                    credit_amount=Decimal("0.00"),
                    description="Recognize accounts receivable",
                ),
                JournalEntryLineInput(
                    account_id=sales_revenue.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=normalized_amount,
                    description="Recognize invoiced revenue",
                ),
            ],
        )

    if normalized_status == "cancelled" and await _journal_entry_exists_for_source(
        session,
        tenant_id=tenant_id,
        source_type="invoice",
        source_id=invoice_id,
        source_event=INVOICE_ISSUED_EVENT,
    ) and not await _journal_entry_exists_for_source(
        session,
        tenant_id=tenant_id,
        source_type="invoice",
        source_id=invoice_id,
        source_event=INVOICE_CANCELLED_EVENT,
    ):
        await create_journal_entry(
            session,
            tenant_id=tenant_id,
            entry_date=issue_date,
            memo=f"{entry_memo} cancelled",
            currency=normalized_currency,
            source_type="invoice",
            source_id=invoice_id,
            source_event=INVOICE_CANCELLED_EVENT,
            lines=[
                JournalEntryLineInput(
                    account_id=sales_revenue.id,
                    debit_amount=normalized_amount,
                    credit_amount=Decimal("0.00"),
                    description="Reverse invoiced revenue",
                ),
                JournalEntryLineInput(
                    account_id=accounts_receivable.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=normalized_amount,
                    description="Reverse accounts receivable",
                ),
            ],
        )


async def sync_payment_accounting_entries(
    session: AsyncSession,
    *,
    tenant_id: str,
    payment_id: str,
    invoice_id: str,
    invoice_number: str,
    payment_date: datetime,
    currency: str,
    amount: Decimal,
    memo: str | None = None,
) -> None:
    await ensure_default_accounts(session, tenant_id=tenant_id)

    accounts_receivable = await _get_account_by_system_key(
        session,
        tenant_id=tenant_id,
        system_key="accounts_receivable",
    )
    cash_account = await _get_account_by_system_key(
        session,
        tenant_id=tenant_id,
        system_key="cash",
    )

    normalized_currency = _normalize_currency(currency)
    normalized_amount = _normalize_decimal(amount)
    entry_memo = memo or f"Payment received for invoice {invoice_number}"

    if await _journal_entry_exists_for_source(
        session,
        tenant_id=tenant_id,
        source_type="payment",
        source_id=payment_id,
        source_event=PAYMENT_COMPLETED_EVENT,
    ):
        return

    await create_journal_entry(
        session,
        tenant_id=tenant_id,
        entry_date=payment_date.date(),
        memo=entry_memo,
        currency=normalized_currency,
        source_type="payment",
        source_id=payment_id,
        source_event=PAYMENT_COMPLETED_EVENT,
        lines=[
            JournalEntryLineInput(
                account_id=cash_account.id,
                debit_amount=normalized_amount,
                credit_amount=Decimal("0.00"),
                description=f"Cash received for invoice {invoice_number}",
            ),
            JournalEntryLineInput(
                account_id=accounts_receivable.id,
                debit_amount=Decimal("0.00"),
                credit_amount=normalized_amount,
                description=f"Clear accounts receivable for invoice {invoice_number}",
            ),
        ],
    )


async def sync_expense_accounting_entries(
    session: AsyncSession,
    *,
    tenant_id: str,
    expense_id: str,
    title: str,
    expense_date: date,
    currency: str,
    amount: Decimal,
    vendor_name: str | None = None,
) -> None:
    await ensure_default_accounts(session, tenant_id=tenant_id)

    operating_expenses = await _get_account_by_system_key(
        session,
        tenant_id=tenant_id,
        system_key="operating_expenses",
    )
    cash_account = await _get_account_by_system_key(
        session,
        tenant_id=tenant_id,
        system_key="cash",
    )

    normalized_currency = _normalize_currency(currency)
    normalized_amount = _normalize_decimal(amount)
    vendor_suffix = f" · {vendor_name}" if vendor_name else ""

    if await _journal_entry_exists_for_source(
        session,
        tenant_id=tenant_id,
        source_type="expense",
        source_id=expense_id,
        source_event=EXPENSE_PAID_EVENT,
    ):
        return

    await create_journal_entry(
        session,
        tenant_id=tenant_id,
        entry_date=expense_date,
        memo=f"Expense paid · {title}{vendor_suffix}",
        currency=normalized_currency,
        source_type="expense",
        source_id=expense_id,
        source_event=EXPENSE_PAID_EVENT,
        lines=[
            JournalEntryLineInput(
                account_id=operating_expenses.id,
                debit_amount=normalized_amount,
                credit_amount=Decimal("0.00"),
                description=f"Recognize paid expense for {title}",
            ),
            JournalEntryLineInput(
                account_id=cash_account.id,
                debit_amount=Decimal("0.00"),
                credit_amount=normalized_amount,
                description=f"Cash paid for expense {title}",
            ),
        ],
    )


async def get_financial_statements_report(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> FinancialStatementsReport:
    await ensure_default_accounts(session, tenant_id=tenant_id)

    account_rows = list(
        (
            await session.execute(
                text(
                    """
                    select
                        aa.id as account_id,
                        aa.code,
                        aa.name,
                        aa.account_type,
                        je.currency,
                        coalesce(sum(jel.debit_amount), 0) as total_debit,
                        coalesce(sum(jel.credit_amount), 0) as total_credit
                    from public.accounting_accounts aa
                    left join public.journal_entry_lines jel
                      on jel.account_id = aa.id
                     and jel.tenant_id = aa.tenant_id
                    left join public.journal_entries je
                      on je.id = jel.journal_entry_id
                     and je.tenant_id = jel.tenant_id
                    where aa.tenant_id = cast(:tenant_id as varchar)
                    group by aa.id, aa.code, aa.name, aa.account_type, je.currency
                    order by aa.code asc
                    """
                ),
                {"tenant_id": tenant_id},
            )
        ).mappings()
    )

    lines_by_account: dict[str, FinancialStatementLine] = {}
    revenue_total = Decimal("0.00")
    expense_total = Decimal("0.00")
    asset_total = Decimal("0.00")
    liability_total = Decimal("0.00")
    equity_total = Decimal("0.00")
    report_currencies: set[str] = set()

    for row in account_rows:
        currency = row["currency"]
        total_debit = Decimal(str(row["total_debit"] or "0"))
        total_credit = Decimal(str(row["total_credit"] or "0"))
        account_type = str(row["account_type"])
        if account_type in {"asset", "expense"}:
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        account_id = str(row["account_id"])
        current = lines_by_account.get(account_id)
        if current is None:
            current = FinancialStatementLine(
                account_id=account_id,
                code=str(row["code"]),
                name=str(row["name"]),
                account_type=account_type,
                total_amount=Decimal("0.00"),
                currencies=[],
            )
            lines_by_account[account_id] = current

        current.total_amount += balance
        if currency and currency not in current.currencies:
            current.currencies.append(str(currency).upper())
            report_currencies.add(str(currency).upper())

    revenue_lines: list[FinancialStatementLine] = []
    expense_lines: list[FinancialStatementLine] = []
    asset_lines: list[FinancialStatementLine] = []
    liability_lines: list[FinancialStatementLine] = []
    equity_lines: list[FinancialStatementLine] = []

    for line in sorted(lines_by_account.values(), key=lambda item: item.code):
        if line.account_type == "revenue":
            revenue_lines.append(line)
            revenue_total += line.total_amount
        elif line.account_type == "expense":
            expense_lines.append(line)
            expense_total += line.total_amount
        elif line.account_type == "asset":
            asset_lines.append(line)
            asset_total += line.total_amount
        elif line.account_type == "liability":
            liability_lines.append(line)
            liability_total += line.total_amount
        elif line.account_type == "equity":
            equity_lines.append(line)
            equity_total += line.total_amount

    current_earnings = revenue_total - expense_total
    if current_earnings != Decimal("0.00"):
        equity_lines.append(
            FinancialStatementLine(
                account_id="current_earnings",
                code="CURR-EARN",
                name="Current Earnings",
                account_type="equity",
                total_amount=current_earnings,
                currencies=sorted(report_currencies),
            )
        )
        equity_total += current_earnings

    receivables_rows = list(
        (
            await session.execute(
                text(
                    """
                    select
                        i.id,
                        i.number,
                        i.company_id,
                        i.status,
                        i.due_date,
                        i.currency,
                        i.total_amount,
                        coalesce(sum(case when ip.status = 'completed' then ip.amount else 0 end), 0) as paid_amount
                    from public.invoices i
                    left join public.invoice_payments ip
                      on ip.invoice_id = i.id
                     and ip.tenant_id = i.tenant_id
                    where i.tenant_id = cast(:tenant_id as varchar)
                      and i.status in ('issued', 'overdue', 'paid')
                    group by i.id, i.number, i.company_id, i.status, i.due_date, i.currency, i.total_amount, i.created_at
                    order by i.created_at desc, i.id desc
                    """
                ),
                {"tenant_id": tenant_id},
            )
        ).mappings()
    )

    receivable_items: list[ReceivablesInvoiceItem] = []
    receivables_total = Decimal("0.00")
    issued_count = 0
    overdue_count = 0
    paid_count = 0
    receivable_currencies: set[str] = set()
    for row in receivables_rows:
        amount = Decimal(str(row["total_amount"]))
        paid_amount = Decimal(str(row["paid_amount"] or "0"))
        outstanding_amount = max(amount - paid_amount, Decimal("0.00"))
        currency = str(row["currency"]).upper()
        status = str(row["status"])
        if status in {"issued", "overdue"}:
            receivables_total += outstanding_amount
        if status == "issued":
            issued_count += 1
        elif status == "overdue":
            overdue_count += 1
        elif status == "paid":
            paid_count += 1
        receivable_currencies.add(currency)
        receivable_items.append(
            ReceivablesInvoiceItem(
                invoice_id=str(row["id"]),
                invoice_number=str(row["number"]),
                company_id=str(row["company_id"]),
                status=status,
                due_date=row["due_date"],
                currency=currency,
                total_amount=amount,
                paid_amount=paid_amount,
                outstanding_amount=outstanding_amount,
            )
        )

    return FinancialStatementsReport(
        profit_and_loss=ProfitAndLossStatement(
            revenue_lines=revenue_lines,
            expense_lines=expense_lines,
            total_revenue=revenue_total,
            total_expenses=expense_total,
            net_income=revenue_total - expense_total,
            currencies=sorted(report_currencies),
        ),
        balance_sheet=BalanceSheetStatement(
            asset_lines=asset_lines,
            liability_lines=liability_lines,
            equity_lines=equity_lines,
            total_assets=asset_total,
            total_liabilities=liability_total,
            total_equity=equity_total,
            total_liabilities_and_equity=liability_total + equity_total,
            currencies=sorted(report_currencies),
        ),
        receivables=ReceivablesSummary(
            open_receivables_amount=receivables_total,
            issued_invoice_count=issued_count,
            overdue_invoice_count=overdue_count,
            paid_invoice_count=paid_count,
            currencies=sorted(receivable_currencies),
            items=receivable_items,
        ),
        vat_supported=False,
        vat_note="VAT summary is not yet available because invoices do not currently persist tax rates or line-level tax amounts.",
        generated_at=datetime.now(UTC),
    )

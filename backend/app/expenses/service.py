from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import sync_expense_accounting_entries


ALLOWED_EXPENSE_STATUSES: tuple[str, ...] = (
    "draft",
    "submitted",
    "approved",
    "paid",
)


@dataclass(slots=True)
class ExpenseDetails:
    id: str
    tenant_id: str
    title: str
    description: str | None
    amount: Decimal
    currency: str
    expense_date: date
    category: str
    status: str
    vendor_name: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ExpenseListResult:
    items: list[ExpenseDetails]
    total: int


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_required_text(value: str, *, field_label: str, max_length: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_label} is required")
    if len(cleaned) > max_length:
        raise ValueError(f"{field_label} must be {max_length} characters or fewer")
    return cleaned


def _normalize_currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("Currency must be a valid ISO 4217 uppercase 3-letter code")
    return normalized


def _normalize_amount(value: Decimal | str | int | float) -> Decimal:
    if isinstance(value, Decimal):
        normalized = value
    else:
        try:
            normalized = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Expense amounts must be valid decimal values") from exc

    if normalized <= 0:
        raise ValueError("Expense amount must be greater than zero")

    return normalized.quantize(Decimal("0.01"))


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_EXPENSE_STATUSES:
        raise ValueError(
            "Invalid expense status. Allowed values: " + ", ".join(ALLOWED_EXPENSE_STATUSES)
        )
    return normalized


def _expense_from_row(row: dict[str, object]) -> ExpenseDetails:
    return ExpenseDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        title=str(row["title"]),
        description=row["description"],
        amount=Decimal(str(row["amount"])),
        currency=str(row["currency"]),
        expense_date=row["expense_date"],
        category=str(row["category"]),
        status=str(row["status"]),
        vendor_name=row["vendor_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def get_expense(
    session: AsyncSession,
    *,
    tenant_id: str,
    expense_id: str,
) -> ExpenseDetails:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                title,
                description,
                amount,
                currency,
                expense_date,
                category,
                status,
                vendor_name,
                created_at,
                updated_at
            from public.expenses
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:expense_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "expense_id": expense_id},
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(f"Expense does not exist: {expense_id}")
    return _expense_from_row(row)


async def list_expenses(
    session: AsyncSession,
    *,
    tenant_id: str,
    status: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ExpenseListResult:
    normalized_status = _normalize_status(status) if status else None
    normalized_category = _clean_optional(category)

    count_result = await session.execute(
        text(
            """
            select count(*)
            from public.expenses
            where tenant_id = cast(:tenant_id as varchar)
              and (:status is null or status = cast(:status as varchar))
              and (:category is null or lower(category) = lower(cast(:category as varchar)))
            """
        ),
        {
            "tenant_id": tenant_id,
            "status": normalized_status,
            "category": normalized_category,
        },
    )
    total = int(count_result.scalar_one() or 0)

    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                title,
                description,
                amount,
                currency,
                expense_date,
                category,
                status,
                vendor_name,
                created_at,
                updated_at
            from public.expenses
            where tenant_id = cast(:tenant_id as varchar)
              and (:status is null or status = cast(:status as varchar))
              and (:category is null or lower(category) = lower(cast(:category as varchar)))
            order by expense_date desc, created_at desc, id desc
            limit :limit
            offset :offset
            """
        ),
        {
            "tenant_id": tenant_id,
            "status": normalized_status,
            "category": normalized_category,
            "limit": limit,
            "offset": offset,
        },
    )
    items = [_expense_from_row(row) for row in result.mappings()]
    return ExpenseListResult(items=items, total=total)


async def create_expense(
    session: AsyncSession,
    *,
    tenant_id: str,
    title: str,
    description: str | None,
    amount: Decimal | str | int | float,
    currency: str,
    expense_date: date,
    category: str,
    status: str = "draft",
    vendor_name: str | None = None,
) -> ExpenseDetails:
    normalized_title = _normalize_required_text(title, field_label="Expense title", max_length=255)
    normalized_description = _clean_optional(description)
    normalized_amount = _normalize_amount(amount)
    normalized_currency = _normalize_currency(currency)
    normalized_category = _normalize_required_text(category, field_label="Expense category", max_length=64)
    normalized_status = _normalize_status(status)
    normalized_vendor_name = _clean_optional(vendor_name)

    result = await session.execute(
        text(
            """
            insert into public.expenses (
                id,
                tenant_id,
                title,
                description,
                amount,
                currency,
                expense_date,
                category,
                status,
                vendor_name
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:title as varchar),
                :description,
                :amount,
                cast(:currency as varchar),
                :expense_date,
                cast(:category as varchar),
                cast(:status as varchar),
                :vendor_name
            )
            returning
                id,
                tenant_id,
                title,
                description,
                amount,
                currency,
                expense_date,
                category,
                status,
                vendor_name,
                created_at,
                updated_at
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": normalized_title,
            "description": normalized_description,
            "amount": normalized_amount,
            "currency": normalized_currency,
            "expense_date": expense_date,
            "category": normalized_category,
            "status": normalized_status,
            "vendor_name": normalized_vendor_name,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create expense")

    expense = _expense_from_row(row)
    if expense.status == "paid":
        await sync_expense_accounting_entries(
            session,
            tenant_id=tenant_id,
            expense_id=expense.id,
            title=expense.title,
            expense_date=expense.expense_date,
            currency=expense.currency,
            amount=expense.amount,
            vendor_name=expense.vendor_name,
        )

    return expense


async def update_expense(
    session: AsyncSession,
    *,
    tenant_id: str,
    expense_id: str,
    title: str | None = None,
    description: str | None = None,
    amount: Decimal | str | int | float | None = None,
    currency: str | None = None,
    expense_date: date | None = None,
    category: str | None = None,
    status: str | None = None,
    vendor_name: str | None = None,
) -> ExpenseDetails:
    existing = await get_expense(session, tenant_id=tenant_id, expense_id=expense_id)

    if existing.status == "paid":
        raise ValueError("Paid expenses are locked to preserve accounting integrity")

    next_title = (
        _normalize_required_text(title, field_label="Expense title", max_length=255)
        if title is not None
        else existing.title
    )
    next_description = _clean_optional(description) if description is not None else existing.description
    next_amount = _normalize_amount(amount) if amount is not None else existing.amount
    next_currency = _normalize_currency(currency) if currency is not None else existing.currency
    next_expense_date = expense_date if expense_date is not None else existing.expense_date
    next_category = (
        _normalize_required_text(category, field_label="Expense category", max_length=64)
        if category is not None
        else existing.category
    )
    next_status = _normalize_status(status) if status is not None else existing.status
    next_vendor_name = _clean_optional(vendor_name) if vendor_name is not None else existing.vendor_name

    result = await session.execute(
        text(
            """
            update public.expenses
            set title = cast(:title as varchar),
                description = :description,
                amount = :amount,
                currency = cast(:currency as varchar),
                expense_date = :expense_date,
                category = cast(:category as varchar),
                status = cast(:status as varchar),
                vendor_name = :vendor_name,
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:expense_id as varchar)
            returning
                id,
                tenant_id,
                title,
                description,
                amount,
                currency,
                expense_date,
                category,
                status,
                vendor_name,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "expense_id": expense_id,
            "title": next_title,
            "description": next_description,
            "amount": next_amount,
            "currency": next_currency,
            "expense_date": next_expense_date,
            "category": next_category,
            "status": next_status,
            "vendor_name": next_vendor_name,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(f"Expense does not exist: {expense_id}")

    expense = _expense_from_row(row)
    if existing.status != "paid" and expense.status == "paid":
        await sync_expense_accounting_entries(
            session,
            tenant_id=tenant_id,
            expense_id=expense.id,
            title=expense.title,
            expense_date=expense.expense_date,
            currency=expense.currency,
            amount=expense.amount,
            vendor_name=expense.vendor_name,
        )

    return expense

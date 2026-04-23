from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import sync_invoice_accounting_entries
from app.payments.service import get_invoice_completed_payment_total, has_invoice_payments


ALLOWED_INVOICE_STATUSES: tuple[str, ...] = (
    "draft",
    "issued",
    "paid",
    "overdue",
    "cancelled",
)

ALLOWED_INVOICE_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("issued", "cancelled"),
    "issued": ("paid", "overdue", "cancelled"),
    "paid": (),
    "overdue": ("paid", "cancelled"),
    "cancelled": (),
}


@dataclass(slots=True)
class InvoiceDetails:
    id: str
    tenant_id: str
    number: str
    company_id: str
    contact_id: str | None
    product_id: str | None
    source_quote_id: str | None
    subscription_id: str | None
    billing_cycle_id: str | None
    issue_date: date
    due_date: date
    currency: str
    total_amount: Decimal
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class InvoiceListResult:
    items: list[InvoiceDetails]
    total: int


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_currency(currency: str) -> str:
    normalized = currency.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("Currency must be a valid ISO 4217 uppercase 3-letter code")
    return normalized


def _validate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in ALLOWED_INVOICE_STATUSES:
        raise ValueError(
            "Invalid invoice status. Allowed values: "
            + ", ".join(ALLOWED_INVOICE_STATUSES)
        )
    return normalized


def _validate_status_transition(*, current_status: str, next_status: str) -> None:
    if current_status == next_status:
        return

    allowed_targets = ALLOWED_INVOICE_STATUS_TRANSITIONS.get(current_status)
    if allowed_targets is None:
        raise ValueError(f"Invalid current invoice status: {current_status}")

    if next_status not in allowed_targets:
        allowed_text = ", ".join(allowed_targets) if allowed_targets else "no transitions"
        raise ValueError(
            f"Invalid invoice status transition: {current_status} -> {next_status}. "
            f"Allowed transitions: {allowed_text}"
        )


def _invoice_changes_require_reposting(
    existing: InvoiceDetails,
    *,
    company_id: str,
    contact_id: str | None,
    product_id: str | None,
    issue_date: date,
    currency: str,
    total_amount: Decimal,
) -> bool:
    return (
        existing.company_id != company_id
        or existing.contact_id != contact_id
        or existing.product_id != product_id
        or existing.issue_date != issue_date
        or existing.currency != currency
        or existing.total_amount != total_amount
    )


async def _company_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.companies
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:company_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "company_id": company_id,
        },
    )
    return result.scalar_one_or_none() == 1


async def _contact_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    contact_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.contacts
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:contact_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "contact_id": contact_id,
        },
    )
    return result.scalar_one_or_none() == 1


async def _contact_belongs_to_company(
    session: AsyncSession,
    *,
    tenant_id: str,
    contact_id: str,
    company_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select company_id
            from public.contacts
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:contact_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "contact_id": contact_id,
        },
    )
    row = result.mappings().first()
    if not row:
        return False
    return row["company_id"] == company_id


async def _product_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    product_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.products
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:product_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "product_id": product_id,
        },
    )
    return result.scalar_one_or_none() == 1


async def _quote_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    quote_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.quotes
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:quote_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "quote_id": quote_id,
        },
    )
    return result.scalar_one_or_none() == 1


async def _quote_belongs_to_company(
    session: AsyncSession,
    *,
    tenant_id: str,
    quote_id: str,
    company_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select company_id
            from public.quotes
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:quote_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "quote_id": quote_id,
        },
    )
    row = result.mappings().first()
    if not row:
        return False
    return row["company_id"] == company_id


async def _invoice_number_exists(
    session: AsyncSession,
    *,
    number: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.invoices
            where number = cast(:number as varchar)
            """
        ),
        {
            "number": number,
        },
    )
    return result.scalar_one_or_none() == 1


async def _generate_invoice_number(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> str:
    result = await session.execute(
        text(
            """
            select count(*) + 1
            from public.invoices
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
        },
    )
    next_number = int(result.scalar_one())
    candidate = f"INV-{next_number:6d}".replace(" ", "0")

    if await _invoice_number_exists(session, number=candidate):
        candidate = f"INV-{uuid.uuid4().hex[:8].upper()}"

    return candidate


async def create_invoice(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    contact_id: str | None = None,
    product_id: str | None = None,
    source_quote_id: str | None = None,
    issue_date: date,
    due_date: date,
    currency: str,
    total_amount: Decimal,
    notes: str | None = None,
) -> InvoiceDetails:
    invoice_id = str(uuid.uuid4())

    normalized_company_id = company_id.strip()
    normalized_contact_id = _clean_optional(contact_id)
    normalized_product_id = _clean_optional(product_id)
    normalized_source_quote_id = _clean_optional(source_quote_id)
    normalized_currency = _normalize_currency(currency)
    normalized_notes = _clean_optional(notes)

    if not normalized_company_id:
        raise ValueError("Company ID is required")

    if due_date < issue_date:
        raise ValueError("Due date cannot be earlier than issue date")

    if not await _company_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        company_id=normalized_company_id,
    ):
        raise ValueError(f"Company does not exist: {normalized_company_id}")

    if normalized_contact_id is not None and not await _contact_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        contact_id=normalized_contact_id,
    ):
        raise ValueError(f"Contact does not exist: {normalized_contact_id}")

    if normalized_contact_id is not None and not await _contact_belongs_to_company(
        session,
        tenant_id=tenant_id,
        contact_id=normalized_contact_id,
        company_id=normalized_company_id,
    ):
        raise ValueError(
            f"Contact does not belong to company: {normalized_contact_id} -> {normalized_company_id}"
        )

    if normalized_product_id is not None and not await _product_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        product_id=normalized_product_id,
    ):
        raise ValueError(f"Product does not exist: {normalized_product_id}")

    if normalized_source_quote_id is not None and not await _quote_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        quote_id=normalized_source_quote_id,
    ):
        raise ValueError(f"Quote does not exist: {normalized_source_quote_id}")

    if normalized_source_quote_id is not None and not await _quote_belongs_to_company(
        session,
        tenant_id=tenant_id,
        quote_id=normalized_source_quote_id,
        company_id=normalized_company_id,
    ):
        raise ValueError(
            f"Quote does not belong to company: {normalized_source_quote_id} -> {normalized_company_id}"
        )

    invoice_number = await _generate_invoice_number(session, tenant_id=tenant_id)

    result = await session.execute(
        text(
            """
            insert into public.invoices (
                id,
                tenant_id,
                number,
                company_id,
                contact_id,
                product_id,
                source_quote_id,
                subscription_id,
                billing_cycle_id,
                issue_date,
                due_date,
                currency,
                total_amount,
                status,
                notes
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:number as varchar),
                cast(:company_id as varchar),
                cast(:contact_id as varchar),
                cast(:product_id as varchar),
                cast(:source_quote_id as varchar),
                cast(:subscription_id as varchar),
                cast(:billing_cycle_id as varchar),
                :issue_date,
                :due_date,
                cast(:currency as varchar),
                :total_amount,
                cast(:status as varchar),
                :notes
            )
            returning
                id,
                tenant_id,
                number,
                company_id,
                contact_id,
                product_id,
                source_quote_id,
                subscription_id,
                billing_cycle_id,
                issue_date,
                due_date,
                currency,
                total_amount,
                status,
                notes,
                created_at,
                updated_at
            """
        ),
        {
            "id": invoice_id,
            "tenant_id": tenant_id,
            "number": invoice_number,
            "company_id": normalized_company_id,
            "contact_id": normalized_contact_id,
            "product_id": normalized_product_id,
            "source_quote_id": normalized_source_quote_id,
            "subscription_id": None,
            "billing_cycle_id": None,
            "issue_date": issue_date,
            "due_date": due_date,
            "currency": normalized_currency,
            "total_amount": total_amount,
            "status": "draft",
            "notes": normalized_notes,
        },
    )

    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create invoice")

    return InvoiceDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        number=str(row["number"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        product_id=row["product_id"],
        source_quote_id=row["source_quote_id"],
        subscription_id=row["subscription_id"],
        billing_cycle_id=row["billing_cycle_id"],
        issue_date=row["issue_date"],
        due_date=row["due_date"],
        currency=str(row["currency"]),
        total_amount=row["total_amount"],
        status=str(row["status"]),
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def get_invoice_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> InvoiceDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                number,
                company_id,
                contact_id,
                product_id,
                source_quote_id,
                subscription_id,
                billing_cycle_id,
                issue_date,
                due_date,
                currency,
                total_amount,
                status,
                notes,
                created_at,
                updated_at
            from public.invoices
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:invoice_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
        },
    )
    row = result.mappings().first()
    if not row:
        return None

    return InvoiceDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        number=str(row["number"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        product_id=row["product_id"],
        source_quote_id=row["source_quote_id"],
        subscription_id=row["subscription_id"],
        billing_cycle_id=row["billing_cycle_id"],
        issue_date=row["issue_date"],
        due_date=row["due_date"],
        currency=str(row["currency"]),
        total_amount=row["total_amount"],
        status=str(row["status"]),
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_invoices(
    session: AsyncSession,
    *,
    tenant_id: str,
    q: str | None = None,
    status: str | None = None,
    company_id: str | None = None,
    number_query: str | None = None,
    source_quote_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> InvoiceListResult:
    search = _clean_optional(q)
    status_filter_raw = _clean_optional(status)
    status_filter = _validate_status(status_filter_raw) if status_filter_raw else None
    company_filter = _clean_optional(company_id)
    number_search = _clean_optional(number_query)
    source_quote_filter = _clean_optional(source_quote_id)

    count_sql = """
        select count(*)
        from public.invoices
        where tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            id,
            tenant_id,
            number,
            company_id,
            contact_id,
            product_id,
            source_quote_id,
            subscription_id,
            billing_cycle_id,
            issue_date,
            due_date,
            currency,
            total_amount,
            status,
            notes,
            created_at,
            updated_at
        from public.invoices
        where tenant_id = cast(:tenant_id as varchar)
    """

    params: dict[str, object] = {
        "tenant_id": tenant_id,
        "limit": limit,
        "offset": offset,
    }

    if search:
        search_clause = """
          and (
                lower(number) like :search
             or lower(currency) like :search
             or lower(status) like :search
             or lower(coalesce(notes, '')) like :search
          )
        """
        count_sql += search_clause
        list_sql += search_clause
        params["search"] = f"%{search.lower()}%"

    if status_filter:
        status_clause = " and status = cast(:status as varchar) "
        count_sql += status_clause
        list_sql += status_clause
        params["status"] = status_filter

    if company_filter:
        company_clause = " and company_id = cast(:company_id as varchar) "
        count_sql += company_clause
        list_sql += company_clause
        params["company_id"] = company_filter

    if number_search:
        number_clause = " and lower(number) like :number_search "
        count_sql += number_clause
        list_sql += number_clause
        params["number_search"] = f"%{number_search.lower()}%"

    if source_quote_filter:
        source_quote_clause = " and source_quote_id = cast(:source_quote_id as varchar) "
        count_sql += source_quote_clause
        list_sql += source_quote_clause
        params["source_quote_id"] = source_quote_filter

    list_sql += """
        order by created_at desc, id desc
        limit :limit
        offset :offset
    """

    count_result = await session.execute(text(count_sql), params)
    total = int(count_result.scalar_one())

    rows_result = await session.execute(text(list_sql), params)

    items: list[InvoiceDetails] = []
    for row in rows_result.mappings():
        items.append(
            InvoiceDetails(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                number=str(row["number"]),
                company_id=str(row["company_id"]),
                contact_id=row["contact_id"],
                product_id=row["product_id"],
                source_quote_id=row["source_quote_id"],
                subscription_id=row["subscription_id"],
                billing_cycle_id=row["billing_cycle_id"],
                issue_date=row["issue_date"],
                due_date=row["due_date"],
                currency=str(row["currency"]),
                total_amount=row["total_amount"],
                status=str(row["status"]),
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return InvoiceListResult(items=items, total=total)


async def update_invoice(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
    company_id: str | None = None,
    contact_id: str | None = None,
    product_id: str | None = None,
    issue_date: date | None = None,
    due_date: date | None = None,
    currency: str | None = None,
    total_amount: Decimal | None = None,
    status: str | None = None,
    notes: str | None = None,
    allow_paid_without_payment: bool = False,
) -> InvoiceDetails:
    existing = await get_invoice_by_id(session, tenant_id=tenant_id, invoice_id=invoice_id)
    if existing is None:
        raise ValueError(f"Invoice does not exist: {invoice_id}")

    effective_company_id = company_id.strip() if company_id is not None else existing.company_id
    effective_contact_id = _clean_optional(contact_id) if contact_id is not None else existing.contact_id
    effective_product_id = _clean_optional(product_id) if product_id is not None else existing.product_id
    effective_issue_date = issue_date if issue_date is not None else existing.issue_date
    effective_due_date = due_date if due_date is not None else existing.due_date
    effective_currency = _normalize_currency(currency) if currency is not None else existing.currency
    effective_total_amount = total_amount if total_amount is not None else existing.total_amount
    effective_status = _validate_status(status) if status is not None else existing.status
    effective_notes = _clean_optional(notes) if notes is not None else existing.notes

    if status is not None:
        _validate_status_transition(current_status=existing.status, next_status=effective_status)

    if (
        effective_status == "paid"
        and existing.status != "paid"
        and not allow_paid_without_payment
    ):
        raise ValueError("Invoice paid status is managed by recorded payments. Record a payment instead.")

    if existing.status != "draft" and _invoice_changes_require_reposting(
        existing,
        company_id=effective_company_id,
        contact_id=effective_contact_id,
        product_id=effective_product_id,
        issue_date=effective_issue_date,
        currency=effective_currency,
        total_amount=effective_total_amount,
    ):
        raise ValueError(
            "Posted invoices can only update status, due date, and notes. "
            "Create a replacement invoice if company, contact, issue date, currency, or amount must change."
        )

    if not effective_company_id:
        raise ValueError("Company ID is required")

    if effective_due_date < effective_issue_date:
        raise ValueError("Due date cannot be earlier than issue date")

    completed_payment_total = await get_invoice_completed_payment_total(
        session,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
    )

    if effective_status == "cancelled" and completed_payment_total > Decimal("0.00"):
        raise ValueError(
            "Invoices with completed payments cannot be cancelled in this launch slice."
        )

    if effective_total_amount < completed_payment_total:
        raise ValueError(
            "Invoice total cannot be reduced below the amount already collected in completed payments."
        )

    if not await _company_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        company_id=effective_company_id,
    ):
        raise ValueError(f"Company does not exist: {effective_company_id}")

    if effective_contact_id is not None and not await _contact_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        contact_id=effective_contact_id,
    ):
        raise ValueError(f"Contact does not exist: {effective_contact_id}")

    if effective_contact_id is not None and not await _contact_belongs_to_company(
        session,
        tenant_id=tenant_id,
        contact_id=effective_contact_id,
        company_id=effective_company_id,
    ):
        raise ValueError(
            f"Contact does not belong to company: {effective_contact_id} -> {effective_company_id}"
        )

    if effective_product_id is not None and not await _product_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        product_id=effective_product_id,
    ):
        raise ValueError(f"Product does not exist: {effective_product_id}")

    result = await session.execute(
        text(
            """
            update public.invoices
            set company_id = cast(:company_id as varchar),
                contact_id = cast(:contact_id as varchar),
                product_id = cast(:product_id as varchar),
                issue_date = :issue_date,
                due_date = :due_date,
                currency = cast(:currency as varchar),
                total_amount = :total_amount,
                status = cast(:status as varchar),
                notes = :notes,
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:invoice_id as varchar)
            returning
                id,
                tenant_id,
                number,
                company_id,
                contact_id,
                product_id,
                source_quote_id,
                subscription_id,
                billing_cycle_id,
                issue_date,
                due_date,
                currency,
                total_amount,
                status,
                notes,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "company_id": effective_company_id,
            "contact_id": effective_contact_id,
            "product_id": effective_product_id,
            "issue_date": effective_issue_date,
            "due_date": effective_due_date,
            "currency": effective_currency,
            "total_amount": effective_total_amount,
            "status": effective_status,
            "notes": effective_notes,
        },
    )

    row = result.mappings().first()
    if not row:
        raise ValueError(f"Invoice does not exist: {invoice_id}")

    invoice = InvoiceDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        number=str(row["number"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        product_id=row["product_id"],
        source_quote_id=row["source_quote_id"],
        subscription_id=row["subscription_id"],
        billing_cycle_id=row["billing_cycle_id"],
        issue_date=row["issue_date"],
        due_date=row["due_date"],
        currency=str(row["currency"]),
        total_amount=row["total_amount"],
        status=str(row["status"]),
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

    if invoice.status != "draft":
        await sync_invoice_accounting_entries(
            session,
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            invoice_number=invoice.number,
            issue_date=invoice.issue_date,
            currency=invoice.currency,
            total_amount=invoice.total_amount,
            status=invoice.status,
            memo=invoice.notes,
        )

    return invoice


async def update_invoice_status(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
    status: str,
) -> InvoiceDetails:
    normalized_status = _validate_status(status)
    return await update_invoice(
        session,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        status=normalized_status,
    )


async def delete_invoice(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> bool:
    if await has_invoice_payments(session, tenant_id=tenant_id, invoice_id=invoice_id):
        raise ValueError("Invoices with recorded payments cannot be deleted.")

    result = await session.execute(
        text(
            """
            delete from public.invoices
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:invoice_id as varchar)
            returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
        },
    )
    row = result.first()
    return row is not None

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.invoicing.service import create_invoice
from app.sales.service import get_deal_by_id


ALLOWED_QUOTE_STATUSES: tuple[str, ...] = (
    "draft",
    "sent",
    "accepted",
    "rejected",
    "expired",
)

ALLOWED_QUOTE_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("sent", "rejected"),
    "sent": ("accepted", "rejected", "expired"),
    "accepted": (),
    "rejected": (),
    "expired": (),
}


@dataclass(slots=True)
class QuoteDetails:
    id: str
    tenant_id: str
    number: str
    company_id: str
    contact_id: str | None
    deal_id: str | None
    source_deal_id: str | None
    product_id: str | None
    issue_date: date
    expiry_date: date
    currency: str
    total_amount: Decimal
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class QuoteListResult:
    items: list[QuoteDetails]
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
    if normalized not in ALLOWED_QUOTE_STATUSES:
        raise ValueError(
            "Invalid quote status. Allowed values: "
            + ", ".join(ALLOWED_QUOTE_STATUSES)
        )
    return normalized


def _validate_status_transition(*, current_status: str, next_status: str) -> None:
    if current_status == next_status:
        return

    allowed_targets = ALLOWED_QUOTE_STATUS_TRANSITIONS.get(current_status)
    if allowed_targets is None:
        raise ValueError(f"Invalid current quote status: {current_status}")

    if next_status not in allowed_targets:
        allowed_text = ", ".join(allowed_targets) if allowed_targets else "no transitions"
        raise ValueError(
            f"Invalid quote status transition: {current_status} -> {next_status}. "
            f"Allowed transitions: {allowed_text}"
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


async def _deal_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    deal_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.deals
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:deal_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "deal_id": deal_id,
        },
    )
    return result.scalar_one_or_none() == 1


async def _deal_belongs_to_company(
    session: AsyncSession,
    *,
    tenant_id: str,
    deal_id: str,
    company_id: str,
) -> bool:
    deal = await get_deal_by_id(session, tenant_id=tenant_id, deal_id=deal_id)
    if deal is None:
        return False
    return deal.company_id == company_id


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


async def _quote_number_exists(
    session: AsyncSession,
    *,
    number: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.quotes
            where number = cast(:number as varchar)
            """
        ),
        {
            "number": number,
        },
    )
    return result.scalar_one_or_none() == 1


async def _generate_quote_number(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> str:
    result = await session.execute(
        text(
            """
            select count(*) + 1
            from public.quotes
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
        },
    )
    next_number = int(result.scalar_one())
    candidate = f"QTE-{next_number:6d}".replace(" ", "0")

    if await _quote_number_exists(session, number=candidate):
        candidate = f"QTE-{uuid.uuid4().hex[:8].upper()}"

    return candidate


async def create_quote(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    contact_id: str | None = None,
    deal_id: str | None = None,
    source_deal_id: str | None = None,
    product_id: str | None = None,
    issue_date: date,
    expiry_date: date,
    currency: str,
    total_amount: Decimal,
    status: str = "draft",
    notes: str | None = None,
) -> QuoteDetails:
    quote_id = str(uuid.uuid4())

    normalized_company_id = company_id.strip()
    normalized_contact_id = _clean_optional(contact_id)
    normalized_deal_id = _clean_optional(deal_id)
    normalized_source_deal_id = _clean_optional(source_deal_id)
    normalized_product_id = _clean_optional(product_id)
    normalized_currency = _normalize_currency(currency)
    normalized_status = _validate_status(status)
    normalized_notes = _clean_optional(notes)

    if not normalized_company_id:
        raise ValueError("Company ID is required")

    if expiry_date < issue_date:
        raise ValueError("Expiry date cannot be earlier than issue date")

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

    if normalized_deal_id is not None and not await _deal_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        deal_id=normalized_deal_id,
    ):
        raise ValueError(f"Deal does not exist: {normalized_deal_id}")

    if normalized_deal_id is not None and not await _deal_belongs_to_company(
        session,
        tenant_id=tenant_id,
        deal_id=normalized_deal_id,
        company_id=normalized_company_id,
    ):
        raise ValueError(
            f"Deal does not belong to company: {normalized_deal_id} -> {normalized_company_id}"
        )

    if normalized_source_deal_id is not None and not await _deal_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        deal_id=normalized_source_deal_id,
    ):
        raise ValueError(f"Deal does not exist: {normalized_source_deal_id}")

    if normalized_source_deal_id is not None and not await _deal_belongs_to_company(
        session,
        tenant_id=tenant_id,
        deal_id=normalized_source_deal_id,
        company_id=normalized_company_id,
    ):
        raise ValueError(
            f"Deal does not belong to company: {normalized_source_deal_id} -> {normalized_company_id}"
        )

    if normalized_product_id is not None and not await _product_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        product_id=normalized_product_id,
    ):
        raise ValueError(f"Product does not exist: {normalized_product_id}")

    quote_number = await _generate_quote_number(session, tenant_id=tenant_id)

    result = await session.execute(
        text(
            """
            insert into public.quotes (
                id,
                tenant_id,
                number,
                company_id,
                contact_id,
                deal_id,
                source_deal_id,
                product_id,
                issue_date,
                expiry_date,
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
                cast(:deal_id as varchar),
                cast(:source_deal_id as varchar),
                cast(:product_id as varchar),
                :issue_date,
                :expiry_date,
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
                deal_id,
                source_deal_id,
                product_id,
                issue_date,
                expiry_date,
                currency,
                total_amount,
                status,
                notes,
                created_at,
                updated_at
            """
        ),
        {
            "id": quote_id,
            "tenant_id": tenant_id,
            "number": quote_number,
            "company_id": normalized_company_id,
            "contact_id": normalized_contact_id,
            "deal_id": normalized_deal_id,
            "source_deal_id": normalized_source_deal_id,
            "product_id": normalized_product_id,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "currency": normalized_currency,
            "total_amount": total_amount,
            "status": normalized_status,
            "notes": normalized_notes,
        },
    )

    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create quote")

    return QuoteDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        number=str(row["number"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        deal_id=row["deal_id"],
        source_deal_id=row["source_deal_id"],
        product_id=row["product_id"],
        issue_date=row["issue_date"],
        expiry_date=row["expiry_date"],
        currency=str(row["currency"]),
        total_amount=row["total_amount"],
        status=str(row["status"]),
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_quotes(
    session: AsyncSession,
    *,
    tenant_id: str,
    q: str | None = None,
    status: str | None = None,
    company_id: str | None = None,
    number_query: str | None = None,
    source_deal_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> QuoteListResult:
    search = _clean_optional(q)
    status_filter_raw = _clean_optional(status)
    status_filter = _validate_status(status_filter_raw) if status_filter_raw else None
    company_filter = _clean_optional(company_id)
    number_search = _clean_optional(number_query)
    source_deal_filter = _clean_optional(source_deal_id)

    count_sql = """
        select count(*)
        from public.quotes
        where tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            id,
            tenant_id,
            number,
            company_id,
            contact_id,
            deal_id,
            source_deal_id,
            product_id,
            issue_date,
            expiry_date,
            currency,
            total_amount,
            status,
            notes,
            created_at,
            updated_at
        from public.quotes
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

    if source_deal_filter:
        source_deal_clause = " and source_deal_id = cast(:source_deal_id as varchar) "
        count_sql += source_deal_clause
        list_sql += source_deal_clause
        params["source_deal_id"] = source_deal_filter

    list_sql += """
        order by created_at desc, id desc
        limit :limit
        offset :offset
    """

    count_result = await session.execute(text(count_sql), params)
    total = int(count_result.scalar_one())

    rows_result = await session.execute(text(list_sql), params)

    items: list[QuoteDetails] = []
    for row in rows_result.mappings():
        items.append(
            QuoteDetails(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                number=str(row["number"]),
                company_id=str(row["company_id"]),
                contact_id=row["contact_id"],
                deal_id=row["deal_id"],
                source_deal_id=row["source_deal_id"],
                product_id=row["product_id"],
                issue_date=row["issue_date"],
                expiry_date=row["expiry_date"],
                currency=str(row["currency"]),
                total_amount=row["total_amount"],
                status=str(row["status"]),
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return QuoteListResult(items=items, total=total)


async def get_quote_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    quote_id: str,
) -> QuoteDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                number,
                company_id,
                contact_id,
                deal_id,
                source_deal_id,
                product_id,
                issue_date,
                expiry_date,
                currency,
                total_amount,
                status,
                notes,
                created_at,
                updated_at
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
        return None

    return QuoteDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        number=str(row["number"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        deal_id=row["deal_id"],
        source_deal_id=row["source_deal_id"],
        product_id=row["product_id"],
        issue_date=row["issue_date"],
        expiry_date=row["expiry_date"],
        currency=str(row["currency"]),
        total_amount=row["total_amount"],
        status=str(row["status"]),
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def convert_deal_to_quote(
    session: AsyncSession,
    *,
    tenant_id: str,
    deal_id: str,
) -> QuoteDetails:
    deal = await get_deal_by_id(session, tenant_id=tenant_id, deal_id=deal_id)
    if deal is None:
        raise ValueError(f"Deal does not exist: {deal_id}")

    issue_date = date.today()
    default_expiry_date = issue_date + timedelta(days=30)
    expiry_date = deal.expected_close_date if deal.expected_close_date and deal.expected_close_date >= issue_date else default_expiry_date

    conversion_note = f"Created from deal {deal.name}"
    deal_notes = deal.notes.strip() if deal.notes else ""
    quote_notes = f"{conversion_note}\n{deal_notes}" if deal_notes else conversion_note

    return await create_quote(
        session,
        tenant_id=tenant_id,
        company_id=deal.company_id,
        contact_id=deal.contact_id,
        deal_id=deal.id,
        source_deal_id=deal.id,
        product_id=deal.product_id,
        issue_date=issue_date,
        expiry_date=expiry_date,
        currency=deal.currency,
        total_amount=deal.amount,
        status="draft",
        notes=quote_notes,
    )


async def convert_quote_to_invoice(
    session: AsyncSession,
    *,
    tenant_id: str,
    quote_id: str,
):
    quote = await get_quote_by_id(session, tenant_id=tenant_id, quote_id=quote_id)
    if quote is None:
        raise ValueError(f"Quote does not exist: {quote_id}")

    if quote.status != "accepted":
        raise ValueError("Only accepted quotes can be converted to invoices")

    conversion_note = f"Converted from quote {quote.number}"
    quote_notes = quote.notes.strip() if quote.notes else ""
    invoice_notes = f"{conversion_note}\n{quote_notes}" if quote_notes else conversion_note

    return await create_invoice(
        session,
        tenant_id=tenant_id,
        company_id=quote.company_id,
        contact_id=quote.contact_id,
        product_id=quote.product_id,
        source_quote_id=quote.id,
        issue_date=quote.issue_date,
        due_date=quote.expiry_date,
        currency=quote.currency,
        total_amount=quote.total_amount,
        notes=invoice_notes,
    )


async def update_quote(
    session: AsyncSession,
    *,
    tenant_id: str,
    quote_id: str,
    company_id: str | None = None,
    contact_id: str | None = None,
    deal_id: str | None = None,
    product_id: str | None = None,
    issue_date: date | None = None,
    expiry_date: date | None = None,
    currency: str | None = None,
    total_amount: Decimal | None = None,
    notes: str | None = None,
) -> QuoteDetails:
    existing = await get_quote_by_id(session, tenant_id=tenant_id, quote_id=quote_id)
    if existing is None:
        raise ValueError(f"Quote does not exist: {quote_id}")

    effective_company_id = company_id.strip() if company_id is not None else existing.company_id
    effective_contact_id = _clean_optional(contact_id) if contact_id is not None else existing.contact_id
    effective_deal_id = _clean_optional(deal_id) if deal_id is not None else existing.deal_id
    effective_product_id = _clean_optional(product_id) if product_id is not None else existing.product_id
    effective_issue_date = issue_date if issue_date is not None else existing.issue_date
    effective_expiry_date = expiry_date if expiry_date is not None else existing.expiry_date
    effective_currency = _normalize_currency(currency) if currency is not None else existing.currency
    effective_total_amount = total_amount if total_amount is not None else existing.total_amount
    effective_notes = _clean_optional(notes) if notes is not None else existing.notes

    if not effective_company_id:
        raise ValueError("Company ID is required")

    if effective_expiry_date < effective_issue_date:
        raise ValueError("Expiry date cannot be earlier than issue date")

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

    if effective_deal_id is not None and not await _deal_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        deal_id=effective_deal_id,
    ):
        raise ValueError(f"Deal does not exist: {effective_deal_id}")

    if effective_product_id is not None and not await _product_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        product_id=effective_product_id,
    ):
        raise ValueError(f"Product does not exist: {effective_product_id}")

    result = await session.execute(
        text(
            """
            update public.quotes
            set company_id = cast(:company_id as varchar),
                contact_id = cast(:contact_id as varchar),
                deal_id = cast(:deal_id as varchar),
                product_id = cast(:product_id as varchar),
                issue_date = :issue_date,
                expiry_date = :expiry_date,
                currency = cast(:currency as varchar),
                total_amount = :total_amount,
                notes = :notes,
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:quote_id as varchar)
            returning
                id,
                tenant_id,
                number,
                company_id,
                contact_id,
                deal_id,
                source_deal_id,
                product_id,
                issue_date,
                expiry_date,
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
            "quote_id": quote_id,
            "company_id": effective_company_id,
            "contact_id": effective_contact_id,
            "deal_id": effective_deal_id,
            "product_id": effective_product_id,
            "issue_date": effective_issue_date,
            "expiry_date": effective_expiry_date,
            "currency": effective_currency,
            "total_amount": effective_total_amount,
            "notes": effective_notes,
        },
    )

    row = result.mappings().first()
    if not row:
        raise ValueError(f"Quote does not exist: {quote_id}")

    return QuoteDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        number=str(row["number"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        deal_id=row["deal_id"],
        source_deal_id=row["source_deal_id"],
        product_id=row["product_id"],
        issue_date=row["issue_date"],
        expiry_date=row["expiry_date"],
        currency=str(row["currency"]),
        total_amount=row["total_amount"],
        status=str(row["status"]),
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def delete_quote(
    session: AsyncSession,
    *,
    tenant_id: str,
    quote_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            delete from public.quotes
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:quote_id as varchar)
            returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "quote_id": quote_id,
        },
    )
    row = result.first()
    return row is not None


async def update_quote_status(
    session: AsyncSession,
    *,
    tenant_id: str,
    quote_id: str,
    status: str,
) -> QuoteDetails:
    existing = await get_quote_by_id(session, tenant_id=tenant_id, quote_id=quote_id)
    if existing is None:
        raise ValueError(f"Quote does not exist: {quote_id}")

    normalized_status = _validate_status(status)
    _validate_status_transition(current_status=existing.status, next_status=normalized_status)

    result = await session.execute(
        text(
            """
            update public.quotes
            set status = cast(:status as varchar),
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:quote_id as varchar)
            returning
                id,
                tenant_id,
                number,
                company_id,
                contact_id,
                deal_id,
                source_deal_id,
                product_id,
                issue_date,
                expiry_date,
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
            "quote_id": quote_id,
            "status": normalized_status,
        },
    )

    row = result.mappings().first()
    if not row:
        raise ValueError(f"Quote does not exist: {quote_id}")

    return QuoteDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        number=str(row["number"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        deal_id=row["deal_id"],
        source_deal_id=row["source_deal_id"],
        product_id=row["product_id"],
        issue_date=row["issue_date"],
        expiry_date=row["expiry_date"],
        currency=str(row["currency"]),
        total_amount=row["total_amount"],
        status=str(row["status"]),
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

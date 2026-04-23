from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
import uuid

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.crm.service import (
    create_company,
    create_contact,
    find_company_by_name,
    find_contact_by_phone_or_email,
    split_contact_name,
)


ALLOWED_DEAL_STAGES: tuple[str, ...] = (
    "new lead",
    "qualified lead",
    "proposal sent",
    "estimate sent",
    "negotiating contract terms",
    "contract signed",
    "deal not secured",
)

ALLOWED_DEAL_STATUSES: tuple[str, ...] = (
    "open",
    "in progress",
    "won",
    "lost",
)

ALLOWED_DEAL_LIST_VIEWS: tuple[str, ...] = (
    "all",
    "opportunities",
)

LEAD_EXPORT_STAGES: tuple[str, ...] = (
    "new lead",
    "qualified lead",
)

LEAD_IMPORT_COLUMNS: tuple[str, ...] = (
    "name",
    "company",
    "first_name",
    "last_name",
    "email",
    "phone",
    "amount",
    "currency",
    "stage",
    "status",
    "source",
    "notes",
)

LEAD_IMPORT_STATUSES: tuple[str, ...] = (
    "open",
    "in progress",
)

_EMAIL_ADAPTER = TypeAdapter(EmailStr)

OPPORTUNITY_DEAL_STAGES: tuple[str, ...] = (
    "qualified lead",
    "proposal sent",
    "estimate sent",
    "negotiating contract terms",
)

OPPORTUNITY_DEAL_STATUSES: tuple[str, ...] = (
    "open",
    "in progress",
)

DEAL_STAGE_FORECAST_WEIGHTS: dict[str, Decimal] = {
    "new lead": Decimal("0.10"),
    "qualified lead": Decimal("0.25"),
    "proposal sent": Decimal("0.50"),
    "estimate sent": Decimal("0.60"),
    "negotiating contract terms": Decimal("0.80"),
    "contract signed": Decimal("1.00"),
    "deal not secured": Decimal("0.00"),
}

ALLOWED_STAGE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "new lead": ("qualified lead", "deal not secured"),
    "qualified lead": ("proposal sent", "estimate sent", "deal not secured"),
    "proposal sent": ("negotiating contract terms", "contract signed", "deal not secured"),
    "estimate sent": ("negotiating contract terms", "contract signed", "deal not secured"),
    "negotiating contract terms": ("contract signed", "deal not secured"),
    "contract signed": (),
    "deal not secured": (),
}

LEGACY_STAGE_ALIASES: dict[str, str] = {
    "lead": "new lead",
    "qualified": "qualified lead",
    "proposal": "proposal sent",
    "estimate": "estimate sent",
    "negotiation": "negotiating contract terms",
    "contracted": "contract signed",
    "won": "contract signed",
    "lost": "deal not secured",
}


@dataclass(slots=True)
class DealDetails:
    id: str
    tenant_id: str
    name: str
    company_id: str
    contact_id: str | None
    product_id: str | None
    amount: Decimal
    currency: str
    stage: str
    status: str
    expected_close_date: date | None
    notes: str | None
    next_follow_up_at: datetime | None
    follow_up_note: str | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class DealListResult:
    items: list[DealDetails]
    total: int


@dataclass(slots=True)
class PipelineStageCount:
    stage: str
    count: int


@dataclass(slots=True)
class PipelineReportResult:
    items: list[PipelineStageCount]
    total: int


@dataclass(slots=True)
class SalesStageSummary:
    stage: str
    count: int
    open_amount: Decimal
    weighted_amount: Decimal


@dataclass(slots=True)
class SalesForecastSummary:
    total_open_pipeline_amount: Decimal
    weighted_pipeline_amount: Decimal
    won_amount: Decimal
    lost_amount: Decimal
    deals_won_this_period_count: int
    deals_won_this_period_amount: Decimal
    deals_lost_this_period_count: int
    deals_lost_this_period_amount: Decimal
    overdue_follow_up_count: int
    due_today_follow_up_count: int
    upcoming_follow_up_count: int
    currencies: list[str]
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


@dataclass(slots=True)
class SalesForecastReportResult:
    summary: SalesForecastSummary
    stage_breakdown: list[SalesStageSummary]
    opportunity_stage_breakdown: list[SalesStageSummary]


@dataclass(slots=True)
class LeadImportRow:
    row_number: int
    name: str | None
    company: str | None
    email: str | None
    stage: str | None
    status: str | None
    result: str
    message: str


@dataclass(slots=True)
class LeadImportResult:
    total_rows: int
    imported_rows: int
    error_rows: int
    rows: list[LeadImportRow]


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_email(value: str | None) -> str | None:
    cleaned = _clean_optional(value)
    return cleaned.lower() if cleaned else None


def _validate_import_email(value: str | None) -> str | None:
    normalized = _normalize_email(value)
    if normalized is None:
        return None

    try:
        validated = _EMAIL_ADAPTER.validate_python(normalized)
    except Exception as exc:  # pragma: no cover - adapter error shape is asserted via row messages
        raise ValueError("Email must be a valid address") from exc

    return str(validated).lower()


def _validate_csv_columns(
    csv_text: str,
    *,
    allowed_columns: tuple[str, ...],
) -> list[dict[str, str]]:
    reader = csv.DictReader(StringIO(csv_text))
    fieldnames = [str(field or "").strip() for field in (reader.fieldnames or [])]
    if not fieldnames:
        raise ValueError("CSV must include a header row")

    unsupported = sorted(column for column in fieldnames if column and column not in allowed_columns)
    if unsupported:
        raise ValueError(
            "CSV contains unsupported columns: " + ", ".join(unsupported)
        )

    return [
        {
            str(key or "").strip(): str(value or "").strip()
            for key, value in row.items()
        }
        for row in reader
    ]


def _normalize_currency(currency: str) -> str:
    normalized = currency.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("Currency must be a valid ISO 4217 uppercase 3-letter code")
    return normalized


def _normalize_money_amount(value: str | Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        normalized = value
    else:
        text_value = _clean_optional(str(value))
        try:
            normalized = Decimal(text_value or "0")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Amount must be a valid decimal amount") from exc

    if normalized < 0:
        raise ValueError("Amount must be zero or greater")

    return normalized.quantize(Decimal("0.01"))


def _normalize_lead_import_stage(stage: str | None) -> str:
    if stage is None:
        return "new lead"

    normalized = _validate_stage(stage)
    if normalized not in LEAD_EXPORT_STAGES:
        raise ValueError(
            "Lead imports only support the stages: "
            + ", ".join(LEAD_EXPORT_STAGES)
        )
    return normalized


def _validate_stage(stage: str) -> str:
    normalized = stage.strip().lower()
    canonical = LEGACY_STAGE_ALIASES.get(normalized, normalized)
    if canonical not in ALLOWED_DEAL_STAGES:
        raise ValueError(
            "Invalid deal stage. Allowed values: "
            + ", ".join(ALLOWED_DEAL_STAGES)
        )
    return canonical


def _validate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in ALLOWED_DEAL_STATUSES:
        raise ValueError(
            "Invalid deal status. Allowed values: "
            + ", ".join(ALLOWED_DEAL_STATUSES)
        )
    return normalized


def _normalize_lead_import_status(status: str | None) -> str:
    if status is None:
        return "open"

    normalized = _validate_status(status)
    if normalized not in LEAD_IMPORT_STATUSES:
        raise ValueError(
            "Lead imports only support the statuses: "
            + ", ".join(LEAD_IMPORT_STATUSES)
        )
    return normalized


def _normalize_list_view(view: str | None) -> str:
    normalized = _clean_optional(view) or "all"
    normalized = normalized.lower()
    if normalized not in ALLOWED_DEAL_LIST_VIEWS:
        raise ValueError(
            "Invalid deal list view. Allowed values: "
            + ", ".join(ALLOWED_DEAL_LIST_VIEWS)
        )
    return normalized


def _is_active_pipeline_status(status: str) -> bool:
    return status in {"open", "in progress"}


def _normalize_follow_up_note(value: str | None) -> str | None:
    return _clean_optional(value)


def _resolve_closed_at_for_status(
    *,
    current_status: str,
    next_status: str,
    existing_closed_at: datetime | None,
    now: datetime,
) -> datetime | None:
    if next_status in {"won", "lost"}:
        if existing_closed_at is not None and current_status == next_status:
            return existing_closed_at
        return now

    return None


def _month_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(
        date(now.year, now.month, 1),
        time.min,
        tzinfo=timezone.utc,
    )
    if now.month == 12:
        end = datetime.combine(date(now.year + 1, 1, 1), time.min, tzinfo=timezone.utc)
    else:
        end = datetime.combine(date(now.year, now.month + 1, 1), time.min, tzinfo=timezone.utc)
    return start, end


def _validate_stage_transition(*, current_stage: str, next_stage: str) -> None:
    normalized_current = LEGACY_STAGE_ALIASES.get(current_stage.strip().lower(), current_stage.strip().lower())
    normalized_next = LEGACY_STAGE_ALIASES.get(next_stage.strip().lower(), next_stage.strip().lower())

    if normalized_current == normalized_next:
        return

    allowed_targets = ALLOWED_STAGE_TRANSITIONS.get(normalized_current)
    if allowed_targets is None:
        raise ValueError(f"Invalid current deal stage: {current_stage}")

    if normalized_next not in allowed_targets:
        allowed_text = ", ".join(allowed_targets) if allowed_targets else "no transitions"
        raise ValueError(
            f"Invalid deal stage transition: {normalized_current} -> {normalized_next}. "
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


async def _get_contact_company_id_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    contact_id: str,
) -> str | None:
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
        return None
    company_id = row["company_id"]
    return str(company_id) if company_id is not None else None


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


async def create_deal(
    session: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    company_id: str,
    contact_id: str | None = None,
    product_id: str | None = None,
    amount: Decimal,
    currency: str,
    stage: str,
    status: str,
    expected_close_date: date | None = None,
    notes: str | None = None,
) -> DealDetails:
    deal_id = str(uuid.uuid4())

    normalized_name = name.strip()
    normalized_company_id = company_id.strip()
    normalized_contact_id = _clean_optional(contact_id)
    normalized_product_id = _clean_optional(product_id)
    normalized_currency = _normalize_currency(currency)
    normalized_stage = _validate_stage(stage)
    normalized_status = _validate_status(status)
    normalized_notes = _clean_optional(notes)
    closed_at = datetime.now(timezone.utc) if normalized_status in {"won", "lost"} else None

    if not normalized_name:
        raise ValueError("Deal name is required")

    if not normalized_company_id:
        raise ValueError("Company ID is required")

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

    if normalized_contact_id is not None:
        contact_company_id = await _get_contact_company_id_for_tenant(
            session,
            tenant_id=tenant_id,
            contact_id=normalized_contact_id,
        )
        if contact_company_id != normalized_company_id:
            raise ValueError("Contact does not belong to the selected company")

    if normalized_product_id is not None and not await _product_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        product_id=normalized_product_id,
    ):
        raise ValueError(f"Product does not exist: {normalized_product_id}")

    result = await session.execute(
        text(
            """
            insert into public.deals (
                id,
                tenant_id,
                name,
                company_id,
                contact_id,
                product_id,
                amount,
                currency,
                stage,
                status,
                expected_close_date,
                notes,
                next_follow_up_at,
                follow_up_note,
                closed_at
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:name as varchar),
                cast(:company_id as varchar),
                cast(:contact_id as varchar),
                cast(:product_id as varchar),
                :amount,
                cast(:currency as varchar),
                cast(:stage as varchar),
                cast(:status as varchar),
                :expected_close_date,
                :notes,
                :next_follow_up_at,
                :follow_up_note,
                :closed_at
            )
            returning
                id,
                tenant_id,
                name,
                company_id,
                contact_id,
                product_id,
                amount,
                currency,
                stage,
                status,
                expected_close_date,
                notes,
                next_follow_up_at,
                follow_up_note,
                closed_at,
                created_at,
                updated_at
            """
        ),
        {
            "id": deal_id,
            "tenant_id": tenant_id,
            "name": normalized_name,
            "company_id": normalized_company_id,
            "contact_id": normalized_contact_id,
            "product_id": normalized_product_id,
            "amount": amount,
            "currency": normalized_currency,
            "stage": normalized_stage,
            "status": normalized_status,
            "expected_close_date": expected_close_date,
            "notes": normalized_notes,
            "next_follow_up_at": None,
            "follow_up_note": None,
            "closed_at": closed_at,
        },
    )

    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create deal")

    return DealDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        product_id=row["product_id"],
        amount=row["amount"],
        currency=str(row["currency"]),
        stage=str(row["stage"]),
        status=str(row["status"]),
        expected_close_date=row["expected_close_date"],
        notes=row["notes"],
        next_follow_up_at=row["next_follow_up_at"],
        follow_up_note=row["follow_up_note"],
        closed_at=row["closed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_lead_from_intake(
    session: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    company_id: str,
    contact_id: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    amount: Decimal = Decimal("0"),
    currency: str = "USD",
    source: str | None = None,
    notes: str | None = None,
) -> DealDetails:
    normalized_email = _clean_optional(email)
    normalized_phone = _clean_optional(phone)
    normalized_source = _clean_optional(source)
    normalized_notes = _clean_optional(notes)

    note_parts: list[str] = []
    if normalized_source:
        note_parts.append(f"Lead source: {normalized_source}")
    if normalized_email:
        note_parts.append(f"Lead email: {normalized_email}")
    if normalized_phone:
        note_parts.append(f"Lead phone: {normalized_phone}")
    if normalized_notes:
        note_parts.append(normalized_notes)

    return await create_deal(
        session,
        tenant_id=tenant_id,
        name=name,
        company_id=company_id,
        contact_id=contact_id,
        product_id=None,
        amount=amount,
        currency=currency,
        stage="new lead",
        status="open",
        expected_close_date=None,
        notes="\n".join(note_parts) if note_parts else None,
    )


async def get_deal_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    deal_id: str,
) -> DealDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                name,
                company_id,
                contact_id,
                product_id,
                amount,
                currency,
                stage,
                status,
                expected_close_date,
                notes,
                next_follow_up_at,
                follow_up_note,
                closed_at,
                created_at,
                updated_at
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
    row = result.mappings().first()
    if not row:
        return None

    return DealDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        product_id=row["product_id"],
        amount=row["amount"],
        currency=str(row["currency"]),
        stage=str(row["stage"]),
        status=str(row["status"]),
        expected_close_date=row["expected_close_date"],
        notes=row["notes"],
        next_follow_up_at=row["next_follow_up_at"],
        follow_up_note=row["follow_up_note"],
        closed_at=row["closed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_deals(
    session: AsyncSession,
    *,
    tenant_id: str,
    view: str | None = None,
    q: str | None = None,
    company_id: str | None = None,
    contact_id: str | None = None,
    product_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> DealListResult:
    normalized_view = _normalize_list_view(view)
    search = _clean_optional(q)
    company_filter = _clean_optional(company_id)
    contact_filter = _clean_optional(contact_id)
    product_filter = _clean_optional(product_id)

    count_sql = """
        select count(*)
        from public.deals
        where tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            id,
            tenant_id,
            name,
            company_id,
            contact_id,
            product_id,
            amount,
            currency,
            stage,
            status,
            expected_close_date,
            notes,
            next_follow_up_at,
            follow_up_note,
            closed_at,
            created_at,
            updated_at
        from public.deals
        where tenant_id = cast(:tenant_id as varchar)
    """

    params: dict[str, object] = {
        "tenant_id": tenant_id,
        "limit": limit,
        "offset": offset,
        "view": normalized_view,
    }

    if normalized_view == "opportunities":
        opportunities_clause = """
          and stage in (
                'qualified lead',
                'proposal sent',
                'estimate sent',
                'negotiating contract terms'
          )
          and status in (
                'open',
                'in progress'
          )
        """
        count_sql += opportunities_clause
        list_sql += opportunities_clause

    if search:
        search_clause = """
          and (
                lower(name) like :search
             or lower(currency) like :search
             or lower(stage) like :search
             or lower(status) like :search
             or lower(coalesce(notes, '')) like :search
          )
        """
        count_sql += search_clause
        list_sql += search_clause
        params["search"] = f"%{search.lower()}%"

    if company_filter:
        company_clause = " and company_id = cast(:company_id as varchar) "
        count_sql += company_clause
        list_sql += company_clause
        params["company_id"] = company_filter

    if contact_filter:
        contact_clause = " and contact_id = cast(:contact_id as varchar) "
        count_sql += contact_clause
        list_sql += contact_clause
        params["contact_id"] = contact_filter

    if product_filter:
        product_clause = " and product_id = cast(:product_id as varchar) "
        count_sql += product_clause
        list_sql += product_clause
        params["product_id"] = product_filter

    list_sql += """
        order by created_at desc, id desc
        limit :limit
        offset :offset
    """

    count_result = await session.execute(text(count_sql), params)
    total = int(count_result.scalar_one())

    rows_result = await session.execute(text(list_sql), params)

    items: list[DealDetails] = []
    for row in rows_result.mappings():
        items.append(
            DealDetails(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                name=str(row["name"]),
                company_id=str(row["company_id"]),
                contact_id=row["contact_id"],
                product_id=row["product_id"],
                amount=row["amount"],
                currency=str(row["currency"]),
                stage=str(row["stage"]),
                status=str(row["status"]),
                expected_close_date=row["expected_close_date"],
                notes=row["notes"],
                next_follow_up_at=row["next_follow_up_at"],
                follow_up_note=row["follow_up_note"],
                closed_at=row["closed_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return DealListResult(items=items, total=total)


async def import_leads_from_csv(
    session: AsyncSession,
    *,
    tenant_id: str,
    csv_text: str,
    create_missing_companies: bool = False,
) -> LeadImportResult:
    rows = _validate_csv_columns(csv_text, allowed_columns=LEAD_IMPORT_COLUMNS)
    output_rows: list[LeadImportRow] = []
    imported_rows = 0
    error_rows = 0

    for index, row in enumerate(rows, start=2):
        name = _clean_optional(row.get("name"))
        company_name = _clean_optional(row.get("company"))
        email = _normalize_email(row.get("email"))
        phone = _clean_optional(row.get("phone"))
        notes = _clean_optional(row.get("notes"))
        source = _clean_optional(row.get("source"))
        stage_value = _clean_optional(row.get("stage"))
        status_value = _clean_optional(row.get("status"))

        try:
            if name is None:
                raise ValueError("name is required")
            if company_name is None:
                raise ValueError("company is required")

            email = _validate_import_email(row.get("email"))

            company = await find_company_by_name(
                session,
                tenant_id=tenant_id,
                company_name=company_name,
            )
            if company is None:
                if not create_missing_companies:
                    raise ValueError(
                        "Company was not found for this tenant. Enable company creation or import the company first."
                    )
                company = await create_company(
                    session,
                    tenant_id=tenant_id,
                    name=company_name,
                )

            stage = _normalize_lead_import_stage(stage_value)
            status = _normalize_lead_import_status(status_value)
            amount = _normalize_money_amount(_clean_optional(row.get("amount")))
            currency = _normalize_currency(_clean_optional(row.get("currency")) or "USD")

            contact_id = None
            contact_first_name = _clean_optional(row.get("first_name"))
            contact_last_name = _clean_optional(row.get("last_name"))
            if any(value for value in (contact_first_name, contact_last_name, email, phone)):
                contact = await find_contact_by_phone_or_email(
                    session,
                    tenant_id=tenant_id,
                    company_id=company.id,
                    phone=phone,
                    email=email,
                )
                if contact is None:
                    if contact_first_name is None:
                        contact_first_name, contact_last_name = split_contact_name(
                            " ".join(part for part in [contact_first_name, contact_last_name] if part),
                            email,
                        )
                    contact = await create_contact(
                        session,
                        tenant_id=tenant_id,
                        first_name=contact_first_name,
                        last_name=contact_last_name,
                        email=email,
                        phone=phone,
                        company_id=company.id,
                        company=company.name,
                        notes=f"Created while importing lead: {name}",
                    )
                contact_id = contact.id

            detail_notes = [notes] if notes else []
            if source:
                detail_notes.append(f"Lead source: {source}")

            await create_deal(
                session,
                tenant_id=tenant_id,
                name=name,
                company_id=company.id,
                contact_id=contact_id,
                product_id=None,
                amount=amount,
                currency=currency,
                stage=stage,
                status=status,
                expected_close_date=None,
                notes="\n".join(detail_notes) if detail_notes else None,
            )

            output_rows.append(
                LeadImportRow(
                    row_number=index,
                    name=name,
                    company=company_name,
                    email=email,
                    stage=stage,
                    status=status,
                    result="imported",
                    message="Imported successfully.",
                )
            )
            imported_rows += 1
        except Exception as exc:
            output_rows.append(
                LeadImportRow(
                    row_number=index,
                    name=name,
                    company=company_name,
                    email=email,
                    stage=stage_value,
                    status=status_value,
                    result="error",
                    message=str(exc),
                )
            )
            error_rows += 1

    return LeadImportResult(
        total_rows=len(rows),
        imported_rows=imported_rows,
        error_rows=error_rows,
        rows=output_rows,
    )


async def export_leads_csv(
    session: AsyncSession,
    *,
    tenant_id: str,
    q: str | None = None,
    company_id: str | None = None,
    contact_id: str | None = None,
) -> tuple[str, int]:
    search = _clean_optional(q)
    company_filter = _clean_optional(company_id)
    contact_filter = _clean_optional(contact_id)
    sql = """
        select
            d.name,
            comp.name as company_name,
            c.first_name,
            c.last_name,
            c.email,
            c.phone,
            d.amount,
            d.currency,
            d.stage,
            d.status,
            d.notes
        from public.deals d
        join public.companies comp
          on comp.id = d.company_id
         and comp.tenant_id = d.tenant_id
        left join public.contacts c
          on c.id = d.contact_id
         and c.tenant_id = d.tenant_id
        where d.tenant_id = cast(:tenant_id as varchar)
          and d.stage in ('new lead', 'qualified lead')
    """
    params: dict[str, object] = {"tenant_id": tenant_id}

    if search:
        sql += """
          and (
                lower(d.name) like :search
             or lower(comp.name) like :search
             or lower(coalesce(c.first_name, '')) like :search
             or lower(coalesce(c.last_name, '')) like :search
             or lower(coalesce(c.email, '')) like :search
             or lower(d.stage) like :search
             or lower(d.status) like :search
             or lower(coalesce(d.notes, '')) like :search
          )
        """
        params["search"] = f"%{search.lower()}%"

    if company_filter:
        sql += " and d.company_id = cast(:company_id as varchar) "
        params["company_id"] = company_filter

    if contact_filter:
        sql += " and d.contact_id = cast(:contact_id as varchar) "
        params["contact_id"] = contact_filter

    sql += " order by d.created_at desc, d.id desc "

    rows = (await session.execute(text(sql), params)).mappings().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "name",
            "company",
            "first_name",
            "last_name",
            "email",
            "phone",
            "amount",
            "currency",
            "stage",
            "status",
            "notes",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["name"] or "",
                row["company_name"] or "",
                row["first_name"] or "",
                row["last_name"] or "",
                row["email"] or "",
                row["phone"] or "",
                row["amount"] or "",
                row["currency"] or "",
                row["stage"] or "",
                row["status"] or "",
                row["notes"] or "",
            ]
        )

    return output.getvalue(), len(rows)


async def get_pipeline_report(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> PipelineReportResult:
    result = await session.execute(
        text(
            """
            select
                stage,
                count(*) as count
            from public.deals
            where tenant_id = cast(:tenant_id as varchar)
            group by stage
            """
        ),
        {
            "tenant_id": tenant_id,
        },
    )

    counts_by_stage: dict[str, int] = {stage: 0 for stage in ALLOWED_DEAL_STAGES}

    for row in result.mappings():
        stage = LEGACY_STAGE_ALIASES.get(str(row["stage"]).strip().lower(), str(row["stage"]).strip().lower())
        count = int(row["count"])
        if stage in counts_by_stage:
            counts_by_stage[stage] = count

    items = [
        PipelineStageCount(stage=stage, count=counts_by_stage[stage])
        for stage in ALLOWED_DEAL_STAGES
    ]

    total = sum(item.count for item in items)

    return PipelineReportResult(items=items, total=total)


async def get_sales_forecast_report(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> SalesForecastReportResult:
    result = await session.execute(
        text(
            """
            select
                stage,
                status,
                amount,
                currency,
                next_follow_up_at,
                closed_at
            from public.deals
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
        },
    )

    now = datetime.now(timezone.utc)
    period_start, period_end = _month_bounds(now)
    zero = Decimal("0.00")

    stage_totals: dict[str, dict[str, Decimal | int]] = {
        stage: {
            "count": 0,
            "open_amount": zero,
            "weighted_amount": zero,
        }
        for stage in ALLOWED_DEAL_STAGES
    }
    opportunity_stage_totals: dict[str, dict[str, Decimal | int]] = {
        stage: {
            "count": 0,
            "open_amount": zero,
            "weighted_amount": zero,
        }
        for stage in OPPORTUNITY_DEAL_STAGES
    }

    total_open_pipeline_amount = zero
    weighted_pipeline_amount = zero
    won_amount = zero
    lost_amount = zero
    deals_won_this_period_count = 0
    deals_won_this_period_amount = zero
    deals_lost_this_period_count = 0
    deals_lost_this_period_amount = zero
    overdue_follow_up_count = 0
    due_today_follow_up_count = 0
    upcoming_follow_up_count = 0
    currencies: set[str] = set()

    for row in result.mappings():
        stage = _validate_stage(str(row["stage"]))
        status = _validate_status(str(row["status"]))
        amount = Decimal(str(row["amount"])).quantize(Decimal("0.01"))
        currencies.add(str(row["currency"]).upper())
        next_follow_up_at = row["next_follow_up_at"]
        closed_at = row["closed_at"]
        weight = DEAL_STAGE_FORECAST_WEIGHTS[stage]

        stage_totals[stage]["count"] = int(stage_totals[stage]["count"]) + 1

        if _is_active_pipeline_status(status):
            stage_totals[stage]["open_amount"] = Decimal(stage_totals[stage]["open_amount"]) + amount
            stage_totals[stage]["weighted_amount"] = (
                Decimal(stage_totals[stage]["weighted_amount"]) + (amount * weight)
            )
            total_open_pipeline_amount += amount
            weighted_pipeline_amount += amount * weight

            if stage in opportunity_stage_totals:
                opportunity_stage_totals[stage]["count"] = int(opportunity_stage_totals[stage]["count"]) + 1
                opportunity_stage_totals[stage]["open_amount"] = (
                    Decimal(opportunity_stage_totals[stage]["open_amount"]) + amount
                )
                opportunity_stage_totals[stage]["weighted_amount"] = (
                    Decimal(opportunity_stage_totals[stage]["weighted_amount"]) + (amount * weight)
                )

            if next_follow_up_at is not None:
                follow_up_at = next_follow_up_at.astimezone(timezone.utc)
                if follow_up_at < now:
                    overdue_follow_up_count += 1
                elif follow_up_at.date() == now.date():
                    due_today_follow_up_count += 1
                else:
                    upcoming_follow_up_count += 1

        if status == "won":
            won_amount += amount
            if closed_at is not None and period_start <= closed_at.astimezone(timezone.utc) < period_end:
                deals_won_this_period_count += 1
                deals_won_this_period_amount += amount

        if status == "lost":
            lost_amount += amount
            if closed_at is not None and period_start <= closed_at.astimezone(timezone.utc) < period_end:
                deals_lost_this_period_count += 1
                deals_lost_this_period_amount += amount

    stage_breakdown = [
        SalesStageSummary(
            stage=stage,
            count=int(stage_totals[stage]["count"]),
            open_amount=Decimal(stage_totals[stage]["open_amount"]).quantize(Decimal("0.01")),
            weighted_amount=Decimal(stage_totals[stage]["weighted_amount"]).quantize(Decimal("0.01")),
        )
        for stage in ALLOWED_DEAL_STAGES
    ]
    opportunity_stage_breakdown = [
        SalesStageSummary(
            stage=stage,
            count=int(opportunity_stage_totals[stage]["count"]),
            open_amount=Decimal(opportunity_stage_totals[stage]["open_amount"]).quantize(Decimal("0.01")),
            weighted_amount=Decimal(opportunity_stage_totals[stage]["weighted_amount"]).quantize(Decimal("0.01")),
        )
        for stage in OPPORTUNITY_DEAL_STAGES
    ]

    return SalesForecastReportResult(
        summary=SalesForecastSummary(
            total_open_pipeline_amount=total_open_pipeline_amount.quantize(Decimal("0.01")),
            weighted_pipeline_amount=weighted_pipeline_amount.quantize(Decimal("0.01")),
            won_amount=won_amount.quantize(Decimal("0.01")),
            lost_amount=lost_amount.quantize(Decimal("0.01")),
            deals_won_this_period_count=deals_won_this_period_count,
            deals_won_this_period_amount=deals_won_this_period_amount.quantize(Decimal("0.01")),
            deals_lost_this_period_count=deals_lost_this_period_count,
            deals_lost_this_period_amount=deals_lost_this_period_amount.quantize(Decimal("0.01")),
            overdue_follow_up_count=overdue_follow_up_count,
            due_today_follow_up_count=due_today_follow_up_count,
            upcoming_follow_up_count=upcoming_follow_up_count,
            currencies=sorted(currencies),
            report_period_start=period_start,
            report_period_end=period_end,
            generated_at=now,
        ),
        stage_breakdown=stage_breakdown,
        opportunity_stage_breakdown=opportunity_stage_breakdown,
    )


async def update_deal(
    session: AsyncSession,
    *,
    tenant_id: str,
    deal_id: str,
    name: str | None = None,
    company_id: str | None = None,
    contact_id: str | None = None,
    product_id: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    stage: str | None = None,
    status: str | None = None,
    expected_close_date: date | None = None,
    notes: str | None = None,
) -> DealDetails:
    existing = await get_deal_by_id(session, tenant_id=tenant_id, deal_id=deal_id)
    if existing is None:
        raise ValueError(f"Deal does not exist: {deal_id}")

    effective_name = name.strip() if name is not None else existing.name
    effective_company_id = company_id.strip() if company_id is not None else existing.company_id
    effective_contact_id = _clean_optional(contact_id) if contact_id is not None else existing.contact_id
    effective_product_id = _clean_optional(product_id) if product_id is not None else existing.product_id
    effective_amount = amount if amount is not None else existing.amount
    effective_currency = _normalize_currency(currency) if currency is not None else existing.currency
    effective_stage = _validate_stage(stage) if stage is not None else existing.stage
    effective_status = _validate_status(status) if status is not None else existing.status
    effective_expected_close_date = (
        expected_close_date if expected_close_date is not None else existing.expected_close_date
    )
    effective_notes = _clean_optional(notes) if notes is not None else existing.notes
    effective_closed_at = _resolve_closed_at_for_status(
        current_status=existing.status,
        next_status=effective_status,
        existing_closed_at=existing.closed_at,
        now=datetime.now(timezone.utc),
    )

    _validate_stage_transition(current_stage=existing.stage, next_stage=effective_stage)

    if not effective_name:
        raise ValueError("Deal name is required")

    if not effective_company_id:
        raise ValueError("Company ID is required")

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

    if effective_contact_id is not None:
        contact_company_id = await _get_contact_company_id_for_tenant(
            session,
            tenant_id=tenant_id,
            contact_id=effective_contact_id,
        )
        if contact_company_id != effective_company_id:
            raise ValueError("Contact does not belong to the selected company")

    if effective_product_id is not None and not await _product_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        product_id=effective_product_id,
    ):
        raise ValueError(f"Product does not exist: {effective_product_id}")

    result = await session.execute(
        text(
            """
            update public.deals
            set name = cast(:name as varchar),
                company_id = cast(:company_id as varchar),
                contact_id = cast(:contact_id as varchar),
                product_id = cast(:product_id as varchar),
                amount = :amount,
                currency = cast(:currency as varchar),
                stage = cast(:stage as varchar),
                status = cast(:status as varchar),
                expected_close_date = :expected_close_date,
                notes = :notes,
                closed_at = :closed_at,
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:deal_id as varchar)
            returning
                id,
                tenant_id,
                name,
                company_id,
                contact_id,
                product_id,
                amount,
                currency,
                stage,
                status,
                expected_close_date,
                notes,
                next_follow_up_at,
                follow_up_note,
                closed_at,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "deal_id": deal_id,
            "name": effective_name,
            "company_id": effective_company_id,
            "contact_id": effective_contact_id,
            "product_id": effective_product_id,
            "amount": effective_amount,
            "currency": effective_currency,
            "stage": effective_stage,
            "status": effective_status,
            "expected_close_date": effective_expected_close_date,
            "notes": effective_notes,
            "closed_at": effective_closed_at,
        },
    )

    row = result.mappings().first()
    if not row:
        raise ValueError(f"Deal does not exist: {deal_id}")

    return DealDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        product_id=row["product_id"],
        amount=row["amount"],
        currency=str(row["currency"]),
        stage=str(row["stage"]),
        status=str(row["status"]),
        expected_close_date=row["expected_close_date"],
        notes=row["notes"],
        next_follow_up_at=row["next_follow_up_at"],
        follow_up_note=row["follow_up_note"],
        closed_at=row["closed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def update_deal_follow_up(
    session: AsyncSession,
    *,
    tenant_id: str,
    deal_id: str,
    next_follow_up_at: datetime | None,
    follow_up_note: str | None,
) -> DealDetails:
    existing = await get_deal_by_id(session, tenant_id=tenant_id, deal_id=deal_id)
    if existing is None:
        raise ValueError(f"Deal does not exist: {deal_id}")

    normalized_follow_up_note = _normalize_follow_up_note(follow_up_note)

    result = await session.execute(
        text(
            """
            update public.deals
            set next_follow_up_at = :next_follow_up_at,
                follow_up_note = :follow_up_note,
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:deal_id as varchar)
            returning
                id,
                tenant_id,
                name,
                company_id,
                contact_id,
                product_id,
                amount,
                currency,
                stage,
                status,
                expected_close_date,
                notes,
                next_follow_up_at,
                follow_up_note,
                closed_at,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "deal_id": deal_id,
            "next_follow_up_at": next_follow_up_at,
            "follow_up_note": normalized_follow_up_note,
        },
    )

    row = result.mappings().first()
    if not row:
        raise ValueError(f"Deal does not exist: {deal_id}")

    return DealDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        company_id=str(row["company_id"]),
        contact_id=row["contact_id"],
        product_id=row["product_id"],
        amount=row["amount"],
        currency=str(row["currency"]),
        stage=str(row["stage"]),
        status=str(row["status"]),
        expected_close_date=row["expected_close_date"],
        notes=row["notes"],
        next_follow_up_at=row["next_follow_up_at"],
        follow_up_note=row["follow_up_note"],
        closed_at=row["closed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def delete_deal(
    session: AsyncSession,
    *,
    tenant_id: str,
    deal_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            delete from public.deals
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:deal_id as varchar)
            returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "deal_id": deal_id,
        },
    )
    row = result.first()
    return row is not None

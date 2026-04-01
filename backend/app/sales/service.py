from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


ALLOWED_DEAL_STAGES: tuple[str, ...] = (
    "lead",
    "new lead",
    "qualified",
    "proposal",
    "estimate",
    "negotiation",
    "contracted",
    "won",
    "lost",
)

ALLOWED_DEAL_STATUSES: tuple[str, ...] = (
    "open",
    "in progress",
    "won",
    "lost",
    "archived",
)

ALLOWED_STAGE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "lead": ("new lead", "qualified", "lost"),
    "new lead": ("qualified", "lost"),
    "qualified": ("proposal", "estimate", "lost"),
    "proposal": ("negotiation", "won", "lost"),
    "estimate": ("negotiation", "won", "lost"),
    "negotiation": ("contracted", "won", "lost"),
    "contracted": ("won", "lost"),
    "won": (),
    "lost": (),
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


def _validate_stage(stage: str) -> str:
    normalized = stage.strip().lower()
    if normalized not in ALLOWED_DEAL_STAGES:
        raise ValueError(
            "Invalid deal stage. Allowed values: "
            + ", ".join(ALLOWED_DEAL_STAGES)
        )
    return normalized


def _validate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in ALLOWED_DEAL_STATUSES:
        raise ValueError(
            "Invalid deal status. Allowed values: "
            + ", ".join(ALLOWED_DEAL_STATUSES)
        )
    return normalized


def _validate_stage_transition(*, current_stage: str, next_stage: str) -> None:
    if current_stage == next_stage:
        return

    allowed_targets = ALLOWED_STAGE_TRANSITIONS.get(current_stage)
    if allowed_targets is None:
        raise ValueError(f"Invalid current deal stage: {current_stage}")

    if next_stage not in allowed_targets:
        allowed_text = ", ".join(allowed_targets) if allowed_targets else "no transitions"
        raise ValueError(
            f"Invalid deal stage transition: {current_stage} -> {next_stage}. "
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
                notes
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
                :notes
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
        created_at=row["created_at"],
        updated_at=row["updated_at"],
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
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_deals(
    session: AsyncSession,
    *,
    tenant_id: str,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> DealListResult:
    search = _clean_optional(q)

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
            created_at,
            updated_at
        from public.deals
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
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return DealListResult(items=items, total=total)


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
        stage = str(row["stage"])
        count = int(row["count"])
        if stage in counts_by_stage:
            counts_by_stage[stage] = count

    items = [
        PipelineStageCount(stage=stage, count=counts_by_stage[stage])
        for stage in ALLOWED_DEAL_STAGES
    ]

    total = sum(item.count for item in items)

    return PipelineReportResult(items=items, total=total)


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
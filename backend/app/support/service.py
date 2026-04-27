from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

UNSET = object()


ALLOWED_TICKET_STATUSES: tuple[str, ...] = (
    "open",
    "in progress",
    "waiting on customer",
    "resolved",
    "closed",
)

ALLOWED_TICKET_PRIORITIES: tuple[str, ...] = (
    "low",
    "medium",
    "high",
    "urgent",
)

ALLOWED_TICKET_SOURCES: tuple[str, ...] = (
    "manual",
    "email",
    "whatsapp",
    "phone",
    "web",
)


@dataclass(slots=True)
class SupportTicketDetails:
    id: str
    tenant_id: str
    title: str
    description: str
    status: str
    priority: str
    source: str
    company_id: str | None
    company_name: str | None
    contact_id: str | None
    contact_name: str | None
    assigned_to_user_id: str | None
    assigned_to_full_name: str | None
    assigned_to_email: str | None
    related_deal_id: str | None
    related_deal_name: str | None
    related_invoice_id: str | None
    related_invoice_number: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class SupportTicketListResult:
    items: list[SupportTicketDetails]
    total: int


@dataclass(slots=True)
class SupportSummary:
    open_count: int
    in_progress_count: int
    urgent_count: int
    resolved_this_period_count: int
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_TICKET_STATUSES:
        raise ValueError(
            "Invalid ticket status. Allowed values: " + ", ".join(ALLOWED_TICKET_STATUSES)
        )
    return normalized


def _normalize_priority(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_TICKET_PRIORITIES:
        raise ValueError(
            "Invalid ticket priority. Allowed values: " + ", ".join(ALLOWED_TICKET_PRIORITIES)
        )
    return normalized


def _normalize_source(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_TICKET_SOURCES:
        raise ValueError(
            "Invalid ticket source. Allowed values: " + ", ".join(ALLOWED_TICKET_SOURCES)
        )
    return normalized


def _month_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(date(now.year, now.month, 1), time.min, tzinfo=timezone.utc)
    if now.month == 12:
        end = datetime.combine(date(now.year + 1, 1, 1), time.min, tzinfo=timezone.utc)
    else:
        end = datetime.combine(date(now.year, now.month + 1, 1), time.min, tzinfo=timezone.utc)
    return start, end


def _ticket_from_row(row: dict[str, object]) -> SupportTicketDetails:
    return SupportTicketDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        title=str(row["title"]),
        description=str(row["description"]),
        status=str(row["status"]),
        priority=str(row["priority"]),
        source=str(row["source"]),
        company_id=row["company_id"],
        company_name=row["company_name"],
        contact_id=row["contact_id"],
        contact_name=row["contact_name"],
        assigned_to_user_id=row["assigned_to_user_id"],
        assigned_to_full_name=row["assigned_to_full_name"],
        assigned_to_email=row["assigned_to_email"],
        related_deal_id=row["related_deal_id"],
        related_deal_name=row["related_deal_name"],
        related_invoice_id=row["related_invoice_id"],
        related_invoice_number=row["related_invoice_number"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
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
        {"tenant_id": tenant_id, "company_id": company_id},
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
        {"tenant_id": tenant_id, "contact_id": contact_id},
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
        {"tenant_id": tenant_id, "contact_id": contact_id},
    )
    row = result.mappings().first()
    if not row:
        return None
    return str(row["company_id"]) if row["company_id"] is not None else None


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
        {"tenant_id": tenant_id, "deal_id": deal_id},
    )
    return result.scalar_one_or_none() == 1


async def _invoice_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.invoices
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:invoice_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "invoice_id": invoice_id},
    )
    return result.scalar_one_or_none() == 1


async def _tenant_user_exists_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.tenant_users
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
              and is_active = true
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    return result.scalar_one_or_none() == 1


async def _validate_ticket_links(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
    contact_id: str | None,
    assigned_to_user_id: str | None,
    related_deal_id: str | None,
    related_invoice_id: str | None,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    normalized_company_id = _clean_optional(company_id)
    normalized_contact_id = _clean_optional(contact_id)
    normalized_assigned_to_user_id = _clean_optional(assigned_to_user_id)
    normalized_related_deal_id = _clean_optional(related_deal_id)
    normalized_related_invoice_id = _clean_optional(related_invoice_id)

    if normalized_company_id is not None and not await _company_exists_for_tenant(
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

    if normalized_company_id is not None and normalized_contact_id is not None:
        contact_company_id = await _get_contact_company_id_for_tenant(
            session,
            tenant_id=tenant_id,
            contact_id=normalized_contact_id,
        )
        if contact_company_id != normalized_company_id:
            raise ValueError("Contact does not belong to the selected company")

    if normalized_assigned_to_user_id is not None and not await _tenant_user_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        user_id=normalized_assigned_to_user_id,
    ):
        raise ValueError(f"Assigned user is not an active member of tenant {tenant_id}: {normalized_assigned_to_user_id}")

    if normalized_related_deal_id is not None and not await _deal_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        deal_id=normalized_related_deal_id,
    ):
        raise ValueError(f"Related deal does not exist: {normalized_related_deal_id}")

    if normalized_related_invoice_id is not None and not await _invoice_exists_for_tenant(
        session,
        tenant_id=tenant_id,
        invoice_id=normalized_related_invoice_id,
    ):
        raise ValueError(f"Related invoice does not exist: {normalized_related_invoice_id}")

    return (
        normalized_company_id,
        normalized_contact_id,
        normalized_assigned_to_user_id,
        normalized_related_deal_id,
        normalized_related_invoice_id,
    )


async def create_ticket(
    session: AsyncSession,
    *,
    tenant_id: str,
    title: str,
    description: str,
    status: str,
    priority: str,
    source: str,
    company_id: str | None = None,
    contact_id: str | None = None,
    assigned_to_user_id: str | None = None,
    related_deal_id: str | None = None,
    related_invoice_id: str | None = None,
) -> SupportTicketDetails:
    normalized_title = title.strip()
    normalized_description = description.strip()
    if not normalized_title:
        raise ValueError("Ticket title is required")
    if not normalized_description:
        raise ValueError("Ticket description is required")

    normalized_status = _normalize_status(status)
    normalized_priority = _normalize_priority(priority)
    normalized_source = _normalize_source(source)
    (
        normalized_company_id,
        normalized_contact_id,
        normalized_assigned_to_user_id,
        normalized_related_deal_id,
        normalized_related_invoice_id,
    ) = await _validate_ticket_links(
        session,
        tenant_id=tenant_id,
        company_id=company_id,
        contact_id=contact_id,
        assigned_to_user_id=assigned_to_user_id,
        related_deal_id=related_deal_id,
        related_invoice_id=related_invoice_id,
    )

    ticket_id = str(uuid.uuid4())
    result = await session.execute(
        text(
            """
            insert into public.support_tickets (
                id,
                tenant_id,
                title,
                description,
                status,
                priority,
                source,
                company_id,
                contact_id,
                assigned_to_user_id,
                related_deal_id,
                related_invoice_id
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:title as varchar),
                :description,
                cast(:status as varchar),
                cast(:priority as varchar),
                cast(:source as varchar),
                cast(:company_id as varchar),
                cast(:contact_id as varchar),
                cast(:assigned_to_user_id as varchar),
                cast(:related_deal_id as varchar),
                cast(:related_invoice_id as varchar)
            )
            returning
                id,
                tenant_id,
                title,
                description,
                status,
                priority,
                source,
                company_id,
                contact_id,
                assigned_to_user_id,
                related_deal_id,
                related_invoice_id,
                created_at,
                updated_at
            """
        ),
        {
            "id": ticket_id,
            "tenant_id": tenant_id,
            "title": normalized_title,
            "description": normalized_description,
            "status": normalized_status,
            "priority": normalized_priority,
            "source": normalized_source,
            "company_id": normalized_company_id,
            "contact_id": normalized_contact_id,
            "assigned_to_user_id": normalized_assigned_to_user_id,
            "related_deal_id": normalized_related_deal_id,
            "related_invoice_id": normalized_related_invoice_id,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create ticket")
    return await get_ticket_by_id(session, tenant_id=tenant_id, ticket_id=str(row["id"])) or _ticket_from_row(row)


async def get_ticket_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    ticket_id: str,
) -> SupportTicketDetails | None:
    result = await session.execute(
        text(
            """
            select
                st.id,
                st.tenant_id,
                st.title,
                st.description,
                st.status,
                st.priority,
                st.source,
                st.company_id,
                c.name as company_name,
                st.contact_id,
                case
                    when ct.id is null then null
                    else concat_ws(' ', ct.first_name, ct.last_name)
                end as contact_name,
                st.assigned_to_user_id,
                u.full_name as assigned_to_full_name,
                u.email as assigned_to_email,
                st.related_deal_id,
                d.name as related_deal_name,
                st.related_invoice_id,
                i.number as related_invoice_number,
                st.created_at,
                st.updated_at
            from public.support_tickets st
            left join public.companies c
              on c.id = st.company_id
             and c.tenant_id = st.tenant_id
            left join public.contacts ct
              on ct.id = st.contact_id
             and ct.tenant_id = st.tenant_id
            left join public.users u
              on u.id = st.assigned_to_user_id
            left join public.deals d
              on d.id = st.related_deal_id
             and d.tenant_id = st.tenant_id
            left join public.invoices i
              on i.id = st.related_invoice_id
             and i.tenant_id = st.tenant_id
            where st.tenant_id = cast(:tenant_id as varchar)
              and st.id = cast(:ticket_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "ticket_id": ticket_id},
    )
    row = result.mappings().first()
    if not row:
        return None
    return _ticket_from_row(row)


async def list_tickets(
    session: AsyncSession,
    *,
    tenant_id: str,
    q: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> SupportTicketListResult:
    search = _clean_optional(q)
    normalized_status = _normalize_status(status) if status else None
    normalized_priority = _normalize_priority(priority) if priority else None

    count_sql = """
        select count(*)
        from public.support_tickets st
        where st.tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            st.id,
            st.tenant_id,
            st.title,
            st.description,
            st.status,
            st.priority,
            st.source,
            st.company_id,
            c.name as company_name,
            st.contact_id,
            case
                when ct.id is null then null
                else concat_ws(' ', ct.first_name, ct.last_name)
            end as contact_name,
            st.assigned_to_user_id,
            u.full_name as assigned_to_full_name,
            u.email as assigned_to_email,
            st.related_deal_id,
            d.name as related_deal_name,
            st.related_invoice_id,
            i.number as related_invoice_number,
            st.created_at,
            st.updated_at
        from public.support_tickets st
        left join public.companies c
          on c.id = st.company_id
         and c.tenant_id = st.tenant_id
        left join public.contacts ct
          on ct.id = st.contact_id
         and ct.tenant_id = st.tenant_id
        left join public.users u
          on u.id = st.assigned_to_user_id
        left join public.deals d
          on d.id = st.related_deal_id
         and d.tenant_id = st.tenant_id
        left join public.invoices i
          on i.id = st.related_invoice_id
         and i.tenant_id = st.tenant_id
        where st.tenant_id = cast(:tenant_id as varchar)
    """
    params: dict[str, object] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

    if search:
        clause = """
          and (
                lower(st.title) like :search
             or lower(st.description) like :search
             or lower(coalesce(c.name, '')) like :search
             or lower(coalesce(ct.first_name, '')) like :search
             or lower(coalesce(ct.last_name, '')) like :search
             or lower(coalesce(u.email, '')) like :search
          )
        """
        count_sql += clause
        list_sql += clause
        params["search"] = f"%{search.lower()}%"

    if normalized_status:
        clause = " and st.status = cast(:status as varchar) "
        count_sql += clause
        list_sql += clause
        params["status"] = normalized_status

    if normalized_priority:
        clause = " and st.priority = cast(:priority as varchar) "
        count_sql += clause
        list_sql += clause
        params["priority"] = normalized_priority

    list_sql += """
        order by st.updated_at desc, st.id desc
        limit :limit
        offset :offset
    """

    total = int((await session.execute(text(count_sql), params)).scalar_one())
    rows = (await session.execute(text(list_sql), params)).mappings().all()
    return SupportTicketListResult(items=[_ticket_from_row(row) for row in rows], total=total)


async def update_ticket(
    session: AsyncSession,
    *,
    tenant_id: str,
    ticket_id: str,
    title: str | None | object = UNSET,
    description: str | None | object = UNSET,
    status: str | None | object = UNSET,
    priority: str | None | object = UNSET,
    source: str | None | object = UNSET,
    company_id: str | None | object = UNSET,
    contact_id: str | None | object = UNSET,
    assigned_to_user_id: str | None | object = UNSET,
    related_deal_id: str | None | object = UNSET,
    related_invoice_id: str | None | object = UNSET,
) -> SupportTicketDetails:
    existing = await get_ticket_by_id(session, tenant_id=tenant_id, ticket_id=ticket_id)
    if existing is None:
        raise ValueError(f"Ticket does not exist: {ticket_id}")

    effective_title = existing.title if title is UNSET else (title.strip() if title is not None else "")
    effective_description = (
        existing.description
        if description is UNSET
        else (description.strip() if description is not None else "")
    )
    if not effective_title:
        raise ValueError("Ticket title is required")
    if not effective_description:
        raise ValueError("Ticket description is required")

    effective_status = existing.status if status is UNSET else _normalize_status(str(status))
    effective_priority = (
        existing.priority if priority is UNSET else _normalize_priority(str(priority))
    )
    effective_source = existing.source if source is UNSET else _normalize_source(str(source))
    (
        normalized_company_id,
        normalized_contact_id,
        normalized_assigned_to_user_id,
        normalized_related_deal_id,
        normalized_related_invoice_id,
    ) = await _validate_ticket_links(
        session,
        tenant_id=tenant_id,
        company_id=existing.company_id if company_id is UNSET else company_id,
        contact_id=existing.contact_id if contact_id is UNSET else contact_id,
        assigned_to_user_id=(
            existing.assigned_to_user_id
            if assigned_to_user_id is UNSET
            else assigned_to_user_id
        ),
        related_deal_id=existing.related_deal_id if related_deal_id is UNSET else related_deal_id,
        related_invoice_id=(
            existing.related_invoice_id
            if related_invoice_id is UNSET
            else related_invoice_id
        ),
    )

    result = await session.execute(
        text(
            """
            update public.support_tickets
            set title = cast(:title as varchar),
                description = :description,
                status = cast(:status as varchar),
                priority = cast(:priority as varchar),
                source = cast(:source as varchar),
                company_id = cast(:company_id as varchar),
                contact_id = cast(:contact_id as varchar),
                assigned_to_user_id = cast(:assigned_to_user_id as varchar),
                related_deal_id = cast(:related_deal_id as varchar),
                related_invoice_id = cast(:related_invoice_id as varchar),
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:ticket_id as varchar)
            returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "ticket_id": ticket_id,
            "title": effective_title,
            "description": effective_description,
            "status": effective_status,
            "priority": effective_priority,
            "source": effective_source,
            "company_id": normalized_company_id,
            "contact_id": normalized_contact_id,
            "assigned_to_user_id": normalized_assigned_to_user_id,
            "related_deal_id": normalized_related_deal_id,
            "related_invoice_id": normalized_related_invoice_id,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(f"Ticket does not exist: {ticket_id}")
    return await get_ticket_by_id(session, tenant_id=tenant_id, ticket_id=ticket_id) or existing


async def get_support_summary(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> SupportSummary:
    now = datetime.now(timezone.utc)
    period_start, period_end = _month_bounds(now)
    result = await session.execute(
        text(
            """
            select
                count(*) filter (where status = 'open') as open_count,
                count(*) filter (where status = 'in progress') as in_progress_count,
                count(*) filter (
                    where priority = 'urgent'
                      and status not in ('resolved', 'closed')
                ) as urgent_count,
                count(*) filter (
                    where status = 'resolved'
                      and updated_at >= :period_start
                      and updated_at < :period_end
                ) as resolved_this_period_count
            from public.support_tickets
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    row = result.mappings().first() or {}
    return SupportSummary(
        open_count=int(row.get("open_count") or 0),
        in_progress_count=int(row.get("in_progress_count") or 0),
        urgent_count=int(row.get("urgent_count") or 0),
        resolved_this_period_count=int(row.get("resolved_this_period_count") or 0),
        report_period_start=period_start,
        report_period_end=period_end,
        generated_at=now,
    )

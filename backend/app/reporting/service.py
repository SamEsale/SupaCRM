from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import FinancialStatementsReport, get_financial_statements_report
from app.sales.service import SalesForecastReportResult, get_sales_forecast_report


@dataclass(slots=True)
class RevenueStatusBreakdown:
    status: str
    count: int
    total_amount: Decimal
    currencies: list[str]


@dataclass(slots=True)
class RevenueFlowSummary:
    quote_count: int
    quote_created_this_period_count: int
    invoice_count: int
    invoice_created_this_period_count: int
    invoice_issued_count: int
    invoice_paid_count: int
    invoice_overdue_count: int
    quote_currencies: list[str]
    invoice_currencies: list[str]
    generated_at: datetime
    report_period_start: datetime
    report_period_end: datetime


@dataclass(slots=True)
class RevenueFlowReport:
    sales_report: SalesForecastReportResult
    summary: RevenueFlowSummary
    quote_status_breakdown: list[RevenueStatusBreakdown]
    invoice_status_breakdown: list[RevenueStatusBreakdown]


@dataclass(slots=True)
class PaymentStatusBreakdown:
    status: str
    count: int
    total_amount: Decimal
    currencies: list[str]


@dataclass(slots=True)
class PaymentsSummary:
    payment_count: int
    completed_payment_count: int
    completed_payment_amount: Decimal
    pending_payment_count: int
    failed_payment_count: int
    cancelled_payment_count: int
    payment_currencies: list[str]
    generated_at: datetime


@dataclass(slots=True)
class FinanceReportsSnapshot:
    revenue_flow: RevenueFlowReport
    financial_statements: FinancialStatementsReport
    payments_summary: PaymentsSummary
    payment_status_breakdown: list[PaymentStatusBreakdown]


@dataclass(slots=True)
class ReportPeriod:
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


@dataclass(slots=True)
class ContactCompanyBreakdown:
    company_id: str | None
    company_name: str
    contact_count: int


@dataclass(slots=True)
class ContactReportItem:
    contact_id: str
    full_name: str
    company_id: str | None
    company_name: str | None
    email: str | None
    phone: str | None
    updated_at: datetime
    open_deals_count: int
    won_deals_count: int
    support_ticket_count: int


@dataclass(slots=True)
class ContactReportsSummary:
    total_contacts: int
    contacts_created_this_period_count: int
    contacts_with_open_deals_count: int
    contacts_with_won_deals_count: int
    contacts_without_company_count: int
    contacts_with_support_tickets_count: int
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


@dataclass(slots=True)
class ContactReportsSnapshot:
    summary: ContactReportsSummary
    contacts_by_company: list[ContactCompanyBreakdown]
    recent_contacts: list[ContactReportItem]


@dataclass(slots=True)
class CompanyContactBreakdown:
    company_id: str
    company_name: str
    contact_count: int


@dataclass(slots=True)
class CompanyReportItem:
    company_id: str
    company_name: str
    updated_at: datetime
    contact_count: int
    open_deals_count: int
    won_deals_count: int
    invoice_count: int
    support_ticket_count: int


@dataclass(slots=True)
class CompanyReportsSummary:
    total_companies: int
    companies_created_this_period_count: int
    companies_with_open_deals_count: int
    companies_with_won_deals_count: int
    companies_with_contacts_count: int
    companies_without_contacts_count: int
    companies_with_invoices_count: int
    companies_with_support_tickets_count: int
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


@dataclass(slots=True)
class CompanyReportsSnapshot:
    summary: CompanyReportsSummary
    contact_breakdown: list[CompanyContactBreakdown]
    recent_companies: list[CompanyReportItem]


@dataclass(slots=True)
class SupportCountBreakdown:
    label: str
    count: int


@dataclass(slots=True)
class SupportCompanyBreakdown:
    company_id: str | None
    company_name: str
    ticket_count: int


@dataclass(slots=True)
class SupportReportItem:
    ticket_id: str
    title: str
    status: str
    priority: str
    source: str
    company_id: str | None
    company_name: str | None
    contact_id: str | None
    related_deal_id: str | None
    related_invoice_id: str | None
    updated_at: datetime


@dataclass(slots=True)
class SupportReportsSummary:
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    waiting_on_customer_tickets: int
    resolved_tickets: int
    closed_tickets: int
    urgent_active_tickets: int
    tickets_linked_to_deals_count: int
    tickets_linked_to_invoices_count: int
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


@dataclass(slots=True)
class SupportReportsSnapshot:
    summary: SupportReportsSummary
    tickets_by_priority: list[SupportCountBreakdown]
    tickets_by_source: list[SupportCountBreakdown]
    tickets_by_company: list[SupportCompanyBreakdown]
    recent_tickets: list[SupportReportItem]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _month_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(date(now.year, now.month, 1), time.min, tzinfo=timezone.utc)
    if now.month == 12:
        end = datetime.combine(date(now.year + 1, 1, 1), time.min, tzinfo=timezone.utc)
    else:
        end = datetime.combine(date(now.year, now.month + 1, 1), time.min, tzinfo=timezone.utc)
    return start, end


async def get_revenue_flow_report(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> RevenueFlowReport:
    sales_report = await get_sales_forecast_report(session, tenant_id=tenant_id)
    period_start = sales_report.summary.report_period_start
    period_end = sales_report.summary.report_period_end

    quotes_result = await session.execute(
        text(
            """
            select status, total_amount, currency, created_at
            from public.quotes
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    invoices_result = await session.execute(
        text(
            """
            select status, total_amount, currency, created_at
            from public.invoices
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )

    quote_rows = list(quotes_result.mappings())
    invoice_rows = list(invoices_result.mappings())

    quote_statuses: dict[str, RevenueStatusBreakdown] = {}
    invoice_statuses: dict[str, RevenueStatusBreakdown] = {}
    quote_currencies: set[str] = set()
    invoice_currencies: set[str] = set()
    quote_created_this_period_count = 0
    invoice_created_this_period_count = 0
    invoice_issued_count = 0
    invoice_paid_count = 0
    invoice_overdue_count = 0

    for row in quote_rows:
        status = str(row["status"])
        currency = str(row["currency"]).upper()
        amount = Decimal(str(row["total_amount"]))
        created_at = row["created_at"]

        quote_currencies.add(currency)
        if period_start <= created_at <= period_end:
            quote_created_this_period_count += 1

        current = quote_statuses.get(status)
        if current is None:
            quote_statuses[status] = RevenueStatusBreakdown(
                status=status,
                count=1,
                total_amount=amount,
                currencies=[currency],
            )
            continue

        current.count += 1
        current.total_amount += amount
        if currency not in current.currencies:
            current.currencies.append(currency)

    for row in invoice_rows:
        status = str(row["status"])
        currency = str(row["currency"]).upper()
        amount = Decimal(str(row["total_amount"]))
        created_at = row["created_at"]

        invoice_currencies.add(currency)
        if period_start <= created_at <= period_end:
            invoice_created_this_period_count += 1

        if status == "issued":
            invoice_issued_count += 1
        elif status == "paid":
            invoice_paid_count += 1
        elif status == "overdue":
            invoice_overdue_count += 1

        current = invoice_statuses.get(status)
        if current is None:
            invoice_statuses[status] = RevenueStatusBreakdown(
                status=status,
                count=1,
                total_amount=amount,
                currencies=[currency],
            )
            continue

        current.count += 1
        current.total_amount += amount
        if currency not in current.currencies:
            current.currencies.append(currency)

    return RevenueFlowReport(
        sales_report=sales_report,
        summary=RevenueFlowSummary(
            quote_count=len(quote_rows),
            quote_created_this_period_count=quote_created_this_period_count,
            invoice_count=len(invoice_rows),
            invoice_created_this_period_count=invoice_created_this_period_count,
            invoice_issued_count=invoice_issued_count,
            invoice_paid_count=invoice_paid_count,
            invoice_overdue_count=invoice_overdue_count,
            quote_currencies=sorted(quote_currencies),
            invoice_currencies=sorted(invoice_currencies),
            generated_at=_now(),
            report_period_start=period_start,
            report_period_end=period_end,
        ),
        quote_status_breakdown=sorted(
            quote_statuses.values(),
            key=lambda item: item.status,
        ),
        invoice_status_breakdown=sorted(
            invoice_statuses.values(),
            key=lambda item: item.status,
        ),
    )


async def get_finance_reports_snapshot(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> FinanceReportsSnapshot:
    revenue_flow, financial_statements = await get_revenue_flow_report(
        session,
        tenant_id=tenant_id,
    ), await get_financial_statements_report(session, tenant_id=tenant_id)

    payments_result = await session.execute(
        text(
            """
            select status, amount, currency, payment_date
            from public.invoice_payments
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    payment_rows = list(payments_result.mappings())
    payment_statuses: dict[str, PaymentStatusBreakdown] = {}
    payment_currencies: set[str] = set()
    completed_payment_count = 0
    completed_payment_amount = Decimal("0.00")
    pending_payment_count = 0
    failed_payment_count = 0
    cancelled_payment_count = 0

    for row in payment_rows:
        status = str(row["status"])
        currency = str(row["currency"]).upper()
        amount = Decimal(str(row["amount"]))
        payment_currencies.add(currency)

        if status == "completed":
            completed_payment_count += 1
            completed_payment_amount += amount
        elif status == "pending":
            pending_payment_count += 1
        elif status == "failed":
            failed_payment_count += 1
        elif status == "cancelled":
            cancelled_payment_count += 1

        current = payment_statuses.get(status)
        if current is None:
            payment_statuses[status] = PaymentStatusBreakdown(
                status=status,
                count=1,
                total_amount=amount,
                currencies=[currency],
            )
            continue

        current.count += 1
        current.total_amount += amount
        if currency not in current.currencies:
            current.currencies.append(currency)

    return FinanceReportsSnapshot(
        revenue_flow=revenue_flow,
        financial_statements=financial_statements,
        payments_summary=PaymentsSummary(
            payment_count=len(payment_rows),
            completed_payment_count=completed_payment_count,
            completed_payment_amount=completed_payment_amount,
            pending_payment_count=pending_payment_count,
            failed_payment_count=failed_payment_count,
            cancelled_payment_count=cancelled_payment_count,
            payment_currencies=sorted(payment_currencies),
            generated_at=_now(),
        ),
        payment_status_breakdown=sorted(
            payment_statuses.values(),
            key=lambda item: item.status,
        ),
    )


async def get_contact_reports_snapshot(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> ContactReportsSnapshot:
    now = _now()
    period_start, period_end = _month_bounds(now)
    summary_result = await session.execute(
        text(
            """
            select
                count(*) as total_contacts,
                count(*) filter (
                    where created_at >= :period_start
                      and created_at < :period_end
                ) as contacts_created_this_period_count,
                count(*) filter (
                    where coalesce(nullif(trim(company_id), ''), nullif(trim(company), '')) is null
                ) as contacts_without_company_count
            from public.contacts
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    summary_row = summary_result.mappings().first() or {}

    open_deal_result = await session.execute(
        text(
            """
            select count(distinct contact_id) as contacts_with_open_deals_count
            from public.deals
            where tenant_id = cast(:tenant_id as varchar)
              and contact_id is not null
              and status in ('open', 'in progress')
            """
        ),
        {"tenant_id": tenant_id},
    )
    open_deal_row = open_deal_result.mappings().first() or {}

    won_deal_result = await session.execute(
        text(
            """
            select count(distinct contact_id) as contacts_with_won_deals_count
            from public.deals
            where tenant_id = cast(:tenant_id as varchar)
              and contact_id is not null
              and status = 'won'
            """
        ),
        {"tenant_id": tenant_id},
    )
    won_deal_row = won_deal_result.mappings().first() or {}

    support_result = await session.execute(
        text(
            """
            select count(distinct contact_id) as contacts_with_support_tickets_count
            from public.support_tickets
            where tenant_id = cast(:tenant_id as varchar)
              and contact_id is not null
            """
        ),
        {"tenant_id": tenant_id},
    )
    support_row = support_result.mappings().first() or {}

    company_breakdown_result = await session.execute(
        text(
            """
            select
                c.company_id,
                coalesce(comp.name, nullif(trim(c.company), ''), 'No company') as company_name,
                count(*) as contact_count
            from public.contacts c
            left join public.companies comp
              on comp.id = c.company_id
             and comp.tenant_id = c.tenant_id
            where c.tenant_id = cast(:tenant_id as varchar)
            group by c.company_id, coalesce(comp.name, nullif(trim(c.company), ''), 'No company')
            order by contact_count desc, company_name asc
            limit 8
            """
        ),
        {"tenant_id": tenant_id},
    )
    recent_contacts_result = await session.execute(
        text(
            """
            select
                c.id as contact_id,
                c.first_name,
                c.last_name,
                c.company_id,
                coalesce(comp.name, nullif(trim(c.company), '')) as company_name,
                c.email,
                c.phone,
                c.updated_at,
                (
                    select count(*)
                    from public.deals d
                    where d.tenant_id = c.tenant_id
                      and d.contact_id = c.id
                      and d.status in ('open', 'in progress')
                ) as open_deals_count,
                (
                    select count(*)
                    from public.deals d
                    where d.tenant_id = c.tenant_id
                      and d.contact_id = c.id
                      and d.status = 'won'
                ) as won_deals_count,
                (
                    select count(*)
                    from public.support_tickets st
                    where st.tenant_id = c.tenant_id
                      and st.contact_id = c.id
                ) as support_ticket_count
            from public.contacts c
            left join public.companies comp
              on comp.id = c.company_id
             and comp.tenant_id = c.tenant_id
            where c.tenant_id = cast(:tenant_id as varchar)
            order by c.updated_at desc, c.id desc
            limit 10
            """
        ),
        {"tenant_id": tenant_id},
    )

    contacts_by_company = [
        ContactCompanyBreakdown(
            company_id=str(row["company_id"]) if row["company_id"] else None,
            company_name=str(row["company_name"]),
            contact_count=int(row["contact_count"] or 0),
        )
        for row in company_breakdown_result.mappings().all()
    ]
    recent_contacts = [
        ContactReportItem(
            contact_id=str(row["contact_id"]),
            full_name=" ".join(
                part for part in [str(row["first_name"]).strip(), str(row["last_name"]).strip() if row["last_name"] else ""] if part
            ),
            company_id=str(row["company_id"]) if row["company_id"] else None,
            company_name=str(row["company_name"]) if row["company_name"] else None,
            email=str(row["email"]) if row["email"] else None,
            phone=str(row["phone"]) if row["phone"] else None,
            updated_at=row["updated_at"],
            open_deals_count=int(row["open_deals_count"] or 0),
            won_deals_count=int(row["won_deals_count"] or 0),
            support_ticket_count=int(row["support_ticket_count"] or 0),
        )
        for row in recent_contacts_result.mappings().all()
    ]

    return ContactReportsSnapshot(
        summary=ContactReportsSummary(
            total_contacts=int(summary_row.get("total_contacts") or 0),
            contacts_created_this_period_count=int(summary_row.get("contacts_created_this_period_count") or 0),
            contacts_with_open_deals_count=int(open_deal_row.get("contacts_with_open_deals_count") or 0),
            contacts_with_won_deals_count=int(won_deal_row.get("contacts_with_won_deals_count") or 0),
            contacts_without_company_count=int(summary_row.get("contacts_without_company_count") or 0),
            contacts_with_support_tickets_count=int(support_row.get("contacts_with_support_tickets_count") or 0),
            report_period_start=period_start,
            report_period_end=period_end,
            generated_at=now,
        ),
        contacts_by_company=contacts_by_company,
        recent_contacts=recent_contacts,
    )


async def get_company_reports_snapshot(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> CompanyReportsSnapshot:
    now = _now()
    period_start, period_end = _month_bounds(now)
    summary_result = await session.execute(
        text(
            """
            select
                count(*) as total_companies,
                count(*) filter (
                    where created_at >= :period_start
                      and created_at < :period_end
                ) as companies_created_this_period_count
            from public.companies
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    summary_row = summary_result.mappings().first() or {}

    open_deal_result = await session.execute(
        text(
            """
            select count(distinct company_id) as companies_with_open_deals_count
            from public.deals
            where tenant_id = cast(:tenant_id as varchar)
              and company_id is not null
              and status in ('open', 'in progress')
            """
        ),
        {"tenant_id": tenant_id},
    )
    won_deal_result = await session.execute(
        text(
            """
            select count(distinct company_id) as companies_with_won_deals_count
            from public.deals
            where tenant_id = cast(:tenant_id as varchar)
              and company_id is not null
              and status = 'won'
            """
        ),
        {"tenant_id": tenant_id},
    )
    contact_result = await session.execute(
        text(
            """
            select count(distinct company_id) as companies_with_contacts_count
            from public.contacts
            where tenant_id = cast(:tenant_id as varchar)
              and company_id is not null
            """
        ),
        {"tenant_id": tenant_id},
    )
    invoice_result = await session.execute(
        text(
            """
            select count(distinct company_id) as companies_with_invoices_count
            from public.invoices
            where tenant_id = cast(:tenant_id as varchar)
              and company_id is not null
            """
        ),
        {"tenant_id": tenant_id},
    )
    support_result = await session.execute(
        text(
            """
            select count(distinct company_id) as companies_with_support_tickets_count
            from public.support_tickets
            where tenant_id = cast(:tenant_id as varchar)
              and company_id is not null
            """
        ),
        {"tenant_id": tenant_id},
    )
    contact_breakdown_result = await session.execute(
        text(
            """
            select
                co.id as company_id,
                co.name as company_name,
                count(c.id) as contact_count
            from public.companies co
            left join public.contacts c
              on c.company_id = co.id
             and c.tenant_id = co.tenant_id
            where co.tenant_id = cast(:tenant_id as varchar)
            group by co.id, co.name
            order by contact_count desc, co.name asc
            limit 8
            """
        ),
        {"tenant_id": tenant_id},
    )
    recent_companies_result = await session.execute(
        text(
            """
            select
                co.id as company_id,
                co.name as company_name,
                co.updated_at,
                (
                    select count(*)
                    from public.contacts c
                    where c.tenant_id = co.tenant_id
                      and c.company_id = co.id
                ) as contact_count,
                (
                    select count(*)
                    from public.deals d
                    where d.tenant_id = co.tenant_id
                      and d.company_id = co.id
                      and d.status in ('open', 'in progress')
                ) as open_deals_count,
                (
                    select count(*)
                    from public.deals d
                    where d.tenant_id = co.tenant_id
                      and d.company_id = co.id
                      and d.status = 'won'
                ) as won_deals_count,
                (
                    select count(*)
                    from public.invoices i
                    where i.tenant_id = co.tenant_id
                      and i.company_id = co.id
                ) as invoice_count,
                (
                    select count(*)
                    from public.support_tickets st
                    where st.tenant_id = co.tenant_id
                      and st.company_id = co.id
                ) as support_ticket_count
            from public.companies co
            where co.tenant_id = cast(:tenant_id as varchar)
            order by co.updated_at desc, co.id desc
            limit 10
            """
        ),
        {"tenant_id": tenant_id},
    )

    contact_row = contact_result.mappings().first() or {}
    total_companies = int(summary_row.get("total_companies") or 0)
    companies_with_contacts_count = int(contact_row.get("companies_with_contacts_count") or 0)

    return CompanyReportsSnapshot(
        summary=CompanyReportsSummary(
            total_companies=total_companies,
            companies_created_this_period_count=int(summary_row.get("companies_created_this_period_count") or 0),
            companies_with_open_deals_count=int((open_deal_result.mappings().first() or {}).get("companies_with_open_deals_count") or 0),
            companies_with_won_deals_count=int((won_deal_result.mappings().first() or {}).get("companies_with_won_deals_count") or 0),
            companies_with_contacts_count=companies_with_contacts_count,
            companies_without_contacts_count=max(0, total_companies - companies_with_contacts_count),
            companies_with_invoices_count=int((invoice_result.mappings().first() or {}).get("companies_with_invoices_count") or 0),
            companies_with_support_tickets_count=int((support_result.mappings().first() or {}).get("companies_with_support_tickets_count") or 0),
            report_period_start=period_start,
            report_period_end=period_end,
            generated_at=now,
        ),
        contact_breakdown=[
            CompanyContactBreakdown(
                company_id=str(row["company_id"]),
                company_name=str(row["company_name"]),
                contact_count=int(row["contact_count"] or 0),
            )
            for row in contact_breakdown_result.mappings().all()
        ],
        recent_companies=[
            CompanyReportItem(
                company_id=str(row["company_id"]),
                company_name=str(row["company_name"]),
                updated_at=row["updated_at"],
                contact_count=int(row["contact_count"] or 0),
                open_deals_count=int(row["open_deals_count"] or 0),
                won_deals_count=int(row["won_deals_count"] or 0),
                invoice_count=int(row["invoice_count"] or 0),
                support_ticket_count=int(row["support_ticket_count"] or 0),
            )
            for row in recent_companies_result.mappings().all()
        ],
    )


async def get_support_reports_snapshot(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> SupportReportsSnapshot:
    now = _now()
    period_start, period_end = _month_bounds(now)
    summary_result = await session.execute(
        text(
            """
            select
                count(*) as total_tickets,
                count(*) filter (where status = 'open') as open_tickets,
                count(*) filter (where status = 'in progress') as in_progress_tickets,
                count(*) filter (where status = 'waiting on customer') as waiting_on_customer_tickets,
                count(*) filter (where status = 'resolved') as resolved_tickets,
                count(*) filter (where status = 'closed') as closed_tickets,
                count(*) filter (
                    where priority = 'urgent'
                      and status not in ('resolved', 'closed')
                ) as urgent_active_tickets,
                count(*) filter (where related_deal_id is not null) as tickets_linked_to_deals_count,
                count(*) filter (where related_invoice_id is not null) as tickets_linked_to_invoices_count
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
    summary_row = summary_result.mappings().first() or {}

    priority_result = await session.execute(
        text(
            """
            select st.priority as label, count(*) as count
            from public.support_tickets st
            where st.tenant_id = cast(:tenant_id as varchar)
            group by st.priority
            order by count desc, label asc
            """
        ),
        {"tenant_id": tenant_id},
    )
    source_result = await session.execute(
        text(
            """
            select st.source as label, count(*) as count
            from public.support_tickets st
            where st.tenant_id = cast(:tenant_id as varchar)
            group by st.source
            order by count desc, label asc
            """
        ),
        {"tenant_id": tenant_id},
    )
    company_result = await session.execute(
        text(
            """
            select
                st.company_id,
                coalesce(comp.name, 'No company linked') as company_name,
                count(*) as ticket_count
            from public.support_tickets st
            left join public.companies comp
              on comp.id = st.company_id
             and comp.tenant_id = st.tenant_id
            where st.tenant_id = cast(:tenant_id as varchar)
            group by st.company_id, coalesce(comp.name, 'No company linked')
            order by ticket_count desc, company_name asc
            limit 8
            """
        ),
        {"tenant_id": tenant_id},
    )
    recent_result = await session.execute(
        text(
            """
            select
                st.id as ticket_id,
                st.title,
                st.status,
                st.priority,
                st.source,
                st.company_id,
                comp.name as company_name,
                st.contact_id,
                st.related_deal_id,
                st.related_invoice_id,
                st.updated_at
            from public.support_tickets st
            left join public.companies comp
              on comp.id = st.company_id
             and comp.tenant_id = st.tenant_id
            where st.tenant_id = cast(:tenant_id as varchar)
            order by st.updated_at desc, st.id desc
            limit 10
            """
        ),
        {"tenant_id": tenant_id},
    )

    return SupportReportsSnapshot(
        summary=SupportReportsSummary(
            total_tickets=int(summary_row.get("total_tickets") or 0),
            open_tickets=int(summary_row.get("open_tickets") or 0),
            in_progress_tickets=int(summary_row.get("in_progress_tickets") or 0),
            waiting_on_customer_tickets=int(summary_row.get("waiting_on_customer_tickets") or 0),
            resolved_tickets=int(summary_row.get("resolved_tickets") or 0),
            closed_tickets=int(summary_row.get("closed_tickets") or 0),
            urgent_active_tickets=int(summary_row.get("urgent_active_tickets") or 0),
            tickets_linked_to_deals_count=int(summary_row.get("tickets_linked_to_deals_count") or 0),
            tickets_linked_to_invoices_count=int(summary_row.get("tickets_linked_to_invoices_count") or 0),
            report_period_start=period_start,
            report_period_end=period_end,
            generated_at=now,
        ),
        tickets_by_priority=[
            SupportCountBreakdown(
                label=str(row["label"]),
                count=int(row["count"] or 0),
            )
            for row in priority_result.mappings().all()
        ],
        tickets_by_source=[
            SupportCountBreakdown(
                label=str(row["label"]),
                count=int(row["count"] or 0),
            )
            for row in source_result.mappings().all()
        ],
        tickets_by_company=[
            SupportCompanyBreakdown(
                company_id=str(row["company_id"]) if row["company_id"] else None,
                company_name=str(row["company_name"]),
                ticket_count=int(row["ticket_count"] or 0),
            )
            for row in company_result.mappings().all()
        ],
        recent_tickets=[
            SupportReportItem(
                ticket_id=str(row["ticket_id"]),
                title=str(row["title"]),
                status=str(row["status"]),
                priority=str(row["priority"]),
                source=str(row["source"]),
                company_id=str(row["company_id"]) if row["company_id"] else None,
                company_name=str(row["company_name"]) if row["company_name"] else None,
                contact_id=str(row["contact_id"]) if row["contact_id"] else None,
                related_deal_id=str(row["related_deal_id"]) if row["related_deal_id"] else None,
                related_invoice_id=str(row["related_invoice_id"]) if row["related_invoice_id"] else None,
                updated_at=row["updated_at"],
            )
            for row in recent_result.mappings().all()
        ],
    )

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.reporting.service import (
    get_company_reports_snapshot,
    get_contact_reports_snapshot,
    get_support_reports_snapshot,
)


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self._rows = rows or []

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)


class FakeReportingSession:
    def __init__(self) -> None:
        self.tenant_ids: list[str] = []

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}
        tenant_id = str(payload.get("tenant_id"))
        self.tenant_ids.append(tenant_id)

        if "total_contacts" in sql and "contacts_without_company_count" in sql:
            return _FakeResult(
                [
                    {
                        "total_contacts": 3,
                        "contacts_created_this_period_count": 2,
                        "contacts_without_company_count": 1,
                    }
                ]
            )
        if "contacts_with_open_deals_count" in sql:
            return _FakeResult([{"contacts_with_open_deals_count": 1}])
        if "contacts_with_won_deals_count" in sql:
            return _FakeResult([{"contacts_with_won_deals_count": 1}])
        if "contacts_with_support_tickets_count" in sql:
            return _FakeResult([{"contacts_with_support_tickets_count": 2}])
        if "from public.contacts c left join public.companies comp" in sql and "group by c.company_id" in sql:
            return _FakeResult(
                [
                    {"company_id": "company-1", "company_name": "Northwind", "contact_count": 2},
                    {"company_id": None, "company_name": "No company", "contact_count": 1},
                ]
            )
        if "from public.contacts c left join public.companies comp" in sql and "order by c.updated_at desc" in sql:
            return _FakeResult(
                [
                    {
                        "contact_id": "contact-1",
                        "first_name": "Alicia",
                        "last_name": "Admin",
                        "company_id": "company-1",
                        "company_name": "Northwind",
                        "email": "alicia@example.com",
                        "phone": "+46-555-01",
                        "updated_at": datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
                        "open_deals_count": 1,
                        "won_deals_count": 1,
                        "support_ticket_count": 2,
                    },
                    {
                        "contact_id": "contact-2",
                        "first_name": "Bo",
                        "last_name": None,
                        "company_id": None,
                        "company_name": None,
                        "email": None,
                        "phone": None,
                        "updated_at": datetime(2026, 4, 13, 8, 0, tzinfo=UTC),
                        "open_deals_count": 0,
                        "won_deals_count": 0,
                        "support_ticket_count": 0,
                    },
                ]
            )

        if "total_companies" in sql and "companies_created_this_period_count" in sql:
            return _FakeResult(
                [
                    {
                        "total_companies": 2,
                        "companies_created_this_period_count": 1,
                    }
                ]
            )
        if "companies_with_open_deals_count" in sql:
            return _FakeResult([{"companies_with_open_deals_count": 1}])
        if "companies_with_won_deals_count" in sql:
            return _FakeResult([{"companies_with_won_deals_count": 1}])
        if "companies_with_contacts_count" in sql:
            return _FakeResult([{"companies_with_contacts_count": 1}])
        if "companies_with_invoices_count" in sql:
            return _FakeResult([{"companies_with_invoices_count": 1}])
        if "companies_with_support_tickets_count" in sql:
            return _FakeResult([{"companies_with_support_tickets_count": 1}])
        if "from public.companies co left join public.contacts c" in sql:
            return _FakeResult(
                [
                    {"company_id": "company-1", "company_name": "Northwind", "contact_count": 2},
                    {"company_id": "company-2", "company_name": "Fabrikam", "contact_count": 0},
                ]
            )
        if "from public.companies co where co.tenant_id" in sql:
            return _FakeResult(
                [
                    {
                        "company_id": "company-1",
                        "company_name": "Northwind",
                        "updated_at": datetime(2026, 4, 14, 10, 0, tzinfo=UTC),
                        "contact_count": 2,
                        "open_deals_count": 1,
                        "won_deals_count": 1,
                        "invoice_count": 1,
                        "support_ticket_count": 1,
                    },
                    {
                        "company_id": "company-2",
                        "company_name": "Fabrikam",
                        "updated_at": datetime(2026, 4, 11, 10, 0, tzinfo=UTC),
                        "contact_count": 0,
                        "open_deals_count": 0,
                        "won_deals_count": 0,
                        "invoice_count": 0,
                        "support_ticket_count": 0,
                    },
                ]
            )

        if "total_tickets" in sql and "waiting_on_customer_tickets" in sql:
            return _FakeResult(
                [
                    {
                        "total_tickets": 5,
                        "open_tickets": 1,
                        "in_progress_tickets": 1,
                        "waiting_on_customer_tickets": 1,
                        "resolved_tickets": 1,
                        "closed_tickets": 1,
                        "urgent_active_tickets": 1,
                        "tickets_linked_to_deals_count": 2,
                        "tickets_linked_to_invoices_count": 1,
                    }
                ]
            )
        if "group by st.priority" in sql:
            return _FakeResult(
                [
                    {"label": "urgent", "count": 1},
                    {"label": "high", "count": 2},
                    {"label": "medium", "count": 2},
                ]
            )
        if "group by st.source" in sql:
            return _FakeResult(
                [
                    {"label": "email", "count": 2},
                    {"label": "manual", "count": 2},
                    {"label": "whatsapp", "count": 1},
                ]
            )
        if "coalesce(comp.name, 'no company linked')" in sql:
            return _FakeResult(
                [
                    {"company_id": "company-1", "company_name": "Northwind", "ticket_count": 3},
                    {"company_id": None, "company_name": "No company linked", "ticket_count": 2},
                ]
            )
        if "from public.support_tickets st left join public.companies comp" in sql and "order by st.updated_at desc" in sql:
            return _FakeResult(
                [
                    {
                        "ticket_id": "ticket-1",
                        "title": "Invoice correction",
                        "status": "open",
                        "priority": "urgent",
                        "source": "email",
                        "company_id": "company-1",
                        "company_name": "Northwind",
                        "contact_id": "contact-1",
                        "related_deal_id": "deal-1",
                        "related_invoice_id": "invoice-1",
                        "updated_at": datetime(2026, 4, 14, 10, 30, tzinfo=UTC),
                    }
                ]
            )

        raise AssertionError(f"Unhandled SQL in FakeReportingSession: {sql}")


@pytest.mark.asyncio
async def test_contact_reports_snapshot_aggregates_recent_contacts_and_company_breakdown() -> None:
    session = FakeReportingSession()

    snapshot = await get_contact_reports_snapshot(session, tenant_id="tenant-1")

    assert all(tenant_id == "tenant-1" for tenant_id in session.tenant_ids)
    assert snapshot.summary.total_contacts == 3
    assert snapshot.summary.contacts_created_this_period_count == 2
    assert snapshot.summary.contacts_with_open_deals_count == 1
    assert snapshot.summary.contacts_with_won_deals_count == 1
    assert snapshot.summary.contacts_without_company_count == 1
    assert snapshot.summary.contacts_with_support_tickets_count == 2
    assert snapshot.contacts_by_company[0].company_name == "Northwind"
    assert snapshot.recent_contacts[0].full_name == "Alicia Admin"
    assert snapshot.recent_contacts[0].support_ticket_count == 2


@pytest.mark.asyncio
async def test_company_reports_snapshot_aggregates_relationship_counts() -> None:
    session = FakeReportingSession()

    snapshot = await get_company_reports_snapshot(session, tenant_id="tenant-1")

    assert all(tenant_id == "tenant-1" for tenant_id in session.tenant_ids)
    assert snapshot.summary.total_companies == 2
    assert snapshot.summary.companies_created_this_period_count == 1
    assert snapshot.summary.companies_with_open_deals_count == 1
    assert snapshot.summary.companies_with_won_deals_count == 1
    assert snapshot.summary.companies_with_contacts_count == 1
    assert snapshot.summary.companies_without_contacts_count == 1
    assert snapshot.summary.companies_with_invoices_count == 1
    assert snapshot.summary.companies_with_support_tickets_count == 1
    assert snapshot.contact_breakdown[0].contact_count == 2
    assert snapshot.recent_companies[0].invoice_count == 1


@pytest.mark.asyncio
async def test_support_reports_snapshot_aggregates_priority_source_and_linkage_counts() -> None:
    session = FakeReportingSession()

    snapshot = await get_support_reports_snapshot(session, tenant_id="tenant-1")

    assert all(tenant_id == "tenant-1" for tenant_id in session.tenant_ids)
    assert snapshot.summary.total_tickets == 5
    assert snapshot.summary.open_tickets == 1
    assert snapshot.summary.in_progress_tickets == 1
    assert snapshot.summary.waiting_on_customer_tickets == 1
    assert snapshot.summary.resolved_tickets == 1
    assert snapshot.summary.closed_tickets == 1
    assert snapshot.summary.urgent_active_tickets == 1
    assert snapshot.summary.tickets_linked_to_deals_count == 2
    assert snapshot.summary.tickets_linked_to_invoices_count == 1
    assert snapshot.tickets_by_priority[0].label == "urgent"
    assert snapshot.tickets_by_source[0].label == "email"
    assert snapshot.tickets_by_company[0].company_name == "Northwind"
    assert snapshot.recent_tickets[0].ticket_id == "ticket-1"

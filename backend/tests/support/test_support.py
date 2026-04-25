from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, get_args

import pytest

from app.support.schemas import SupportTicketPriority, SupportTicketSource, SupportTicketStatus
from app.support.service import (
    ALLOWED_TICKET_PRIORITIES,
    ALLOWED_TICKET_SOURCES,
    ALLOWED_TICKET_STATUSES,
    create_ticket,
    get_support_summary,
    get_ticket_by_id,
    list_tickets,
    update_ticket,
)


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeResult:
    def __init__(self, *, rows: list[dict[str, Any]] | None = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise AssertionError("Expected scalar result")
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakeSupportSession:
    def __init__(self) -> None:
        self.companies = {
            "company-1": {"tenant_id": "tenant-1", "name": "Northwind"},
            "company-2": {"tenant_id": "tenant-1", "name": "Fabrikam"},
        }
        self.contacts = {
            "contact-1": {
                "tenant_id": "tenant-1",
                "company_id": "company-1",
                "first_name": "Alicia",
                "last_name": "Andersson",
            },
            "contact-2": {
                "tenant_id": "tenant-1",
                "company_id": "company-2",
                "first_name": "Bengt",
                "last_name": "Berg",
            },
        }
        self.tenant_users = {
            "user-1": {"tenant_id": "tenant-1", "email": "owner@example.com", "full_name": "Owner User", "is_active": True},
            "user-2": {"tenant_id": "tenant-1", "email": "agent@example.com", "full_name": "Agent User", "is_active": True},
        }
        self.deals = {"deal-1": {"tenant_id": "tenant-1", "name": "Expansion deal"}}
        self.invoices = {"invoice-1": {"tenant_id": "tenant-1", "number": "INV-1001"}}
        self.tickets: dict[str, dict[str, Any]] = {}

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "select 1 from public.companies" in sql:
            company = self.companies.get(str(payload["company_id"]))
            if company and company["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select 1 from public.contacts" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            if contact and contact["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select company_id from public.contacts" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            if contact and contact["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(rows=[{"company_id": contact["company_id"]}])
            return _FakeResult(rows=[])

        if "select 1 from public.tenant_users" in sql:
            user = self.tenant_users.get(str(payload["user_id"]))
            if user and user["tenant_id"] == str(payload["tenant_id"]) and user["is_active"]:
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select 1 from public.deals" in sql:
            deal = self.deals.get(str(payload["deal_id"]))
            if deal and deal["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select 1 from public.invoices" in sql:
            invoice = self.invoices.get(str(payload["invoice_id"]))
            if invoice and invoice["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "insert into public.support_tickets" in sql:
            now = datetime.now(timezone.utc)
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "title": str(payload["title"]),
                "description": str(payload["description"]),
                "status": str(payload["status"]),
                "priority": str(payload["priority"]),
                "source": str(payload["source"]),
                "company_id": payload.get("company_id"),
                "contact_id": payload.get("contact_id"),
                "assigned_to_user_id": payload.get("assigned_to_user_id"),
                "related_deal_id": payload.get("related_deal_id"),
                "related_invoice_id": payload.get("related_invoice_id"),
                "created_at": now,
                "updated_at": now,
            }
            self.tickets[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "from public.support_tickets st" in sql and "where st.tenant_id = cast(:tenant_id as varchar) and st.id = cast(:ticket_id as varchar)" in sql:
            ticket = self.tickets.get(str(payload["ticket_id"]))
            if not ticket or ticket["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[self._decorate_ticket(ticket)])

        if "select count(*) from public.support_tickets st" in sql:
            return _FakeResult(scalar=len(self._filter_tickets(payload)))

        if "from public.support_tickets st" in sql and "order by st.updated_at desc" in sql:
            rows = self._filter_tickets(payload)
            rows.sort(key=lambda row: (row["updated_at"], row["id"]), reverse=True)
            offset = int(payload.get("offset", 0))
            limit = int(payload.get("limit", len(rows)))
            return _FakeResult(rows=[self._decorate_ticket(row) for row in rows[offset : offset + limit]])

        if "update public.support_tickets" in sql:
            ticket = self.tickets.get(str(payload["ticket_id"]))
            if not ticket or ticket["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            ticket.update(
                {
                    "title": str(payload["title"]),
                    "description": str(payload["description"]),
                    "status": str(payload["status"]),
                    "priority": str(payload["priority"]),
                    "source": str(payload["source"]),
                    "company_id": payload.get("company_id"),
                    "contact_id": payload.get("contact_id"),
                    "assigned_to_user_id": payload.get("assigned_to_user_id"),
                    "related_deal_id": payload.get("related_deal_id"),
                    "related_invoice_id": payload.get("related_invoice_id"),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            return _FakeResult(rows=[{"id": ticket["id"]}])

        if "select count(*) filter (where status = 'open')" in sql:
            tenant_id = str(payload["tenant_id"])
            tickets = [ticket for ticket in self.tickets.values() if ticket["tenant_id"] == tenant_id]
            return _FakeResult(
                rows=[
                    {
                        "open_count": sum(1 for ticket in tickets if ticket["status"] == "open"),
                        "in_progress_count": sum(1 for ticket in tickets if ticket["status"] == "in progress"),
                        "urgent_count": sum(
                            1
                            for ticket in tickets
                            if ticket["priority"] == "urgent" and ticket["status"] not in {"resolved", "closed"}
                        ),
                        "resolved_this_period_count": sum(
                            1
                            for ticket in tickets
                            if ticket["status"] == "resolved"
                            and payload["period_start"] <= ticket["updated_at"] < payload["period_end"]
                        ),
                    }
                ]
            )

        raise AssertionError(f"Unhandled SQL in FakeSupportSession: {sql}")

    def _decorate_ticket(self, row: dict[str, Any]) -> dict[str, Any]:
        company = self.companies.get(str(row["company_id"])) if row.get("company_id") else None
        contact = self.contacts.get(str(row["contact_id"])) if row.get("contact_id") else None
        user = self.tenant_users.get(str(row["assigned_to_user_id"])) if row.get("assigned_to_user_id") else None
        deal = self.deals.get(str(row["related_deal_id"])) if row.get("related_deal_id") else None
        invoice = self.invoices.get(str(row["related_invoice_id"])) if row.get("related_invoice_id") else None
        return {
            **row,
            "company_name": company["name"] if company else None,
            "contact_name": " ".join([contact["first_name"], contact["last_name"]]) if contact else None,
            "assigned_to_full_name": user["full_name"] if user else None,
            "assigned_to_email": user["email"] if user else None,
            "related_deal_name": deal["name"] if deal else None,
            "related_invoice_number": invoice["number"] if invoice else None,
        }

    def _filter_tickets(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = [dict(ticket) for ticket in self.tickets.values() if ticket["tenant_id"] == str(payload["tenant_id"])]
        search = str(payload.get("search", "")).replace("%", "").lower()
        if search:
            rows = [
                row
                for row in rows
                if search in " ".join(
                    [
                        row["title"],
                        row["description"],
                        self.companies.get(str(row["company_id"]), {}).get("name", ""),
                        self.contacts.get(str(row["contact_id"]), {}).get("first_name", ""),
                        self.contacts.get(str(row["contact_id"]), {}).get("last_name", ""),
                    ]
                ).lower()
            ]
        if payload.get("status"):
            rows = [row for row in rows if row["status"] == str(payload["status"])]
        if payload.get("priority"):
            rows = [row for row in rows if row["priority"] == str(payload["priority"])]
        return rows


@pytest.fixture
def session() -> FakeSupportSession:
    return FakeSupportSession()


@pytest.mark.asyncio
async def test_support_contract_matches_exposed_schema() -> None:
    assert ALLOWED_TICKET_STATUSES == get_args(SupportTicketStatus)
    assert ALLOWED_TICKET_PRIORITIES == get_args(SupportTicketPriority)
    assert ALLOWED_TICKET_SOURCES == get_args(SupportTicketSource)


@pytest.mark.asyncio
async def test_create_ticket_and_get_detail(session: FakeSupportSession) -> None:
    ticket = await create_ticket(
        session,
        tenant_id="tenant-1",
        title="Invoice question",
        description="Customer needs a corrected invoice.",
        status="open",
        priority="high",
        source="email",
        company_id="company-1",
        contact_id="contact-1",
        assigned_to_user_id="user-2",
        related_deal_id="deal-1",
        related_invoice_id="invoice-1",
    )

    loaded = await get_ticket_by_id(session, tenant_id="tenant-1", ticket_id=ticket.id)

    assert loaded is not None
    assert loaded.company_name == "Northwind"
    assert loaded.contact_name == "Alicia Andersson"
    assert loaded.assigned_to_email == "agent@example.com"
    assert loaded.related_invoice_number == "INV-1001"


@pytest.mark.asyncio
async def test_update_ticket_can_clear_optional_links(session: FakeSupportSession) -> None:
    created = await create_ticket(
        session,
        tenant_id="tenant-1",
        title="Clear support links",
        description="Ticket should allow clearing CRM and commercial references.",
        status="open",
        priority="medium",
        source="manual",
        company_id="company-1",
        contact_id="contact-1",
        assigned_to_user_id="user-2",
        related_deal_id="deal-1",
        related_invoice_id="invoice-1",
    )

    updated = await update_ticket(
        session,
        tenant_id="tenant-1",
        ticket_id=created.id,
        contact_id=None,
        assigned_to_user_id=None,
        related_deal_id=None,
        related_invoice_id=None,
    )

    assert updated.company_id == "company-1"
    assert updated.contact_id is None
    assert updated.assigned_to_user_id is None
    assert updated.related_deal_id is None
    assert updated.related_invoice_id is None


@pytest.mark.asyncio
async def test_create_and_update_ticket_reject_contact_company_mismatch(session: FakeSupportSession) -> None:
    with pytest.raises(ValueError, match="Contact does not belong to the selected company"):
        await create_ticket(
            session,
            tenant_id="tenant-1",
            title="Mismatch",
            description="Bad CRM linkage",
            status="open",
            priority="medium",
            source="manual",
            company_id="company-1",
            contact_id="contact-2",
        )

    created = await create_ticket(
        session,
        tenant_id="tenant-1",
        title="Valid ticket",
        description="Needs update",
        status="open",
        priority="medium",
        source="manual",
        company_id="company-1",
        contact_id="contact-1",
    )

    with pytest.raises(ValueError, match="Contact does not belong to the selected company"):
        await update_ticket(
            session,
            tenant_id="tenant-1",
            ticket_id=created.id,
            company_id="company-1",
            contact_id="contact-2",
        )


@pytest.mark.asyncio
async def test_update_ticket_validates_related_entities(session: FakeSupportSession) -> None:
    created = await create_ticket(
        session,
        tenant_id="tenant-1",
        title="Assignment needed",
        description="Link this ticket",
        status="open",
        priority="medium",
        source="phone",
    )

    with pytest.raises(ValueError, match="Assigned user is not an active member"):
        await update_ticket(
            session,
            tenant_id="tenant-1",
            ticket_id=created.id,
            assigned_to_user_id="user-x",
        )

    with pytest.raises(ValueError, match="Related deal does not exist"):
        await update_ticket(
            session,
            tenant_id="tenant-1",
            ticket_id=created.id,
            related_deal_id="deal-x",
        )

    with pytest.raises(ValueError, match="Related invoice does not exist"):
        await update_ticket(
            session,
            tenant_id="tenant-1",
            ticket_id=created.id,
            related_invoice_id="invoice-x",
        )


@pytest.mark.asyncio
async def test_list_tickets_filters_and_summary(session: FakeSupportSession) -> None:
    first = await create_ticket(
        session,
        tenant_id="tenant-1",
        title="Open urgent",
        description="Needs attention",
        status="open",
        priority="urgent",
        source="whatsapp",
        company_id="company-1",
        contact_id="contact-1",
    )
    await create_ticket(
        session,
        tenant_id="tenant-1",
        title="Resolved medium",
        description="Already done",
        status="resolved",
        priority="medium",
        source="manual",
    )
    await update_ticket(
        session,
        tenant_id="tenant-1",
        ticket_id=first.id,
        status="in progress",
        priority="urgent",
    )

    filtered = await list_tickets(
        session,
        tenant_id="tenant-1",
        q="open",
        priority="urgent",
    )
    summary = await get_support_summary(session, tenant_id="tenant-1")

    assert filtered.total == 1
    assert filtered.items[0].status == "in progress"
    assert summary.in_progress_count == 1
    assert summary.urgent_count == 1
    assert summary.resolved_this_period_count == 1

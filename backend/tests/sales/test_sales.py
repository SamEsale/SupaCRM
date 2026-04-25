from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, get_args

import pytest

from app.sales.schemas import DealStatus
from app.sales.service import (
    ALLOWED_DEAL_STAGES,
    ALLOWED_DEAL_STATUSES,
    create_deal,
    create_lead_from_intake,
    delete_deal,
    get_deal_by_id,
    get_pipeline_report,
    get_sales_forecast_report,
    list_deals,
    update_deal_follow_up,
    update_deal,
)


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def __iter__(self):
        return iter(self._rows)


class _FakeResult:
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        scalar: Any = None,
        first_row: Any = None,
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar
        self._first_row = first_row

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise AssertionError("Expected scalar result but found none")
        return self._scalar

    def first(self) -> Any:
        if self._first_row is not None:
            return self._first_row
        return self._rows[0] if self._rows else None


class FakeSalesSession:
    def __init__(self) -> None:
        self.companies = {
            "company-1": {
                "id": "company-1",
                "tenant_id": "tenant-1",
                "name": "Northwind Labs",
            },
            "company-2": {
                "id": "company-2",
                "tenant_id": "tenant-1",
                "name": "Fabrikam",
            },
            "company-3": {
                "id": "company-3",
                "tenant_id": "tenant-2",
                "name": "Outside tenant",
            },
        }
        self.contacts = {
            "contact-1": {
                "id": "contact-1",
                "tenant_id": "tenant-1",
                "company_id": "company-1",
            },
            "contact-2": {
                "id": "contact-2",
                "tenant_id": "tenant-1",
                "company_id": "company-2",
            },
        }
        self.products = {
            "product-1": {
                "id": "product-1",
                "tenant_id": "tenant-1",
            },
        }
        self.deals: dict[str, dict[str, Any]] = {}

    async def execute(
        self,
        statement: Any,
        params: dict[str, Any] | None = None,
    ) -> _FakeResult:
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

        if "select 1 from public.products" in sql:
            product = self.products.get(str(payload["product_id"]))
            if product and product["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "insert into public.deals" in sql:
            now = datetime.now(timezone.utc)
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "name": str(payload["name"]),
                "company_id": str(payload["company_id"]),
                "contact_id": payload.get("contact_id"),
                "product_id": payload.get("product_id"),
                "amount": Decimal(str(payload["amount"])),
                "currency": str(payload["currency"]),
                "stage": str(payload["stage"]),
                "status": str(payload["status"]),
                "expected_close_date": payload.get("expected_close_date"),
                "notes": payload.get("notes"),
                "next_follow_up_at": payload.get("next_follow_up_at"),
                "follow_up_note": payload.get("follow_up_note"),
                "closed_at": payload.get("closed_at"),
                "created_at": now,
                "updated_at": now,
            }
            self.deals[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if (
            "from public.deals where tenant_id = cast(:tenant_id as varchar) and id = cast(:deal_id as varchar)"
            in sql
            and "select" in sql
        ):
            deal = self.deals.get(str(payload["deal_id"]))
            if not deal or deal["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(deal)])

        if "select count(*) from public.deals" in sql:
            filtered = self._filter_deals(payload)
            return _FakeResult(scalar=len(filtered))

        if "from public.deals where tenant_id = cast(:tenant_id as varchar)" in sql and "order by created_at desc" in sql:
            filtered = self._filter_deals(payload)
            filtered.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
            offset = int(payload.get("offset", 0))
            limit = int(payload.get("limit", len(filtered)))
            return _FakeResult(rows=[dict(row) for row in filtered[offset : offset + limit]])

        if "select stage, count(*) as count from public.deals" in sql:
            tenant_id = str(payload["tenant_id"])
            counts: dict[str, int] = {}
            for deal in self.deals.values():
                if deal["tenant_id"] != tenant_id:
                    continue
                counts[deal["stage"]] = counts.get(deal["stage"], 0) + 1
            return _FakeResult(
                rows=[{"stage": stage, "count": count} for stage, count in counts.items()],
            )

        if "select stage, status, amount, currency, next_follow_up_at, closed_at" in sql:
            tenant_id = str(payload["tenant_id"])
            rows = [
                {
                    "stage": deal["stage"],
                    "status": deal["status"],
                    "amount": deal["amount"],
                    "currency": deal["currency"],
                    "next_follow_up_at": deal["next_follow_up_at"],
                    "closed_at": deal["closed_at"],
                }
                for deal in self.deals.values()
                if deal["tenant_id"] == tenant_id
            ]
            return _FakeResult(rows=rows)

        if "update public.deals set" in sql:
            deal = self.deals.get(str(payload["deal_id"]))
            if not deal or deal["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            if "next_follow_up_at" in payload and "follow_up_note" in payload and "name" not in payload:
                deal.update(
                    {
                        "next_follow_up_at": payload.get("next_follow_up_at"),
                        "follow_up_note": payload.get("follow_up_note"),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
            else:
                deal.update(
                    {
                        "name": str(payload["name"]),
                        "company_id": str(payload["company_id"]),
                        "contact_id": payload.get("contact_id"),
                        "product_id": payload.get("product_id"),
                        "amount": Decimal(str(payload["amount"])),
                        "currency": str(payload["currency"]),
                        "stage": str(payload["stage"]),
                        "status": str(payload["status"]),
                        "expected_close_date": payload.get("expected_close_date"),
                        "notes": payload.get("notes"),
                        "closed_at": payload.get("closed_at"),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
            return _FakeResult(rows=[dict(deal)])

        if "delete from public.deals" in sql:
            deal = self.deals.get(str(payload["deal_id"]))
            if not deal or deal["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(first_row=None)
            self.deals.pop(str(payload["deal_id"]), None)
            return _FakeResult(first_row={"id": payload["deal_id"]})

        raise AssertionError(f"Unhandled SQL in FakeSalesSession: {sql}")

    def _filter_deals(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        tenant_id = str(payload["tenant_id"])
        search = str(payload.get("search", "")).replace("%", "").lower()
        company_id = payload.get("company_id")
        contact_id = payload.get("contact_id")
        product_id = payload.get("product_id")
        view = payload.get("view")

        rows = [dict(deal) for deal in self.deals.values() if deal["tenant_id"] == tenant_id]

        if view == "opportunities":
            rows = [
                row
                for row in rows
                if row["stage"] in {
                    "qualified lead",
                    "proposal sent",
                    "estimate sent",
                    "negotiating contract terms",
                }
                and row["status"] in {"open", "in progress"}
            ]

        if search:
            rows = [
                row
                for row in rows
                if search in " ".join(
                    [
                        str(row["name"]),
                        str(row["currency"]),
                        str(row["stage"]),
                        str(row["status"]),
                        str(row["notes"] or ""),
                    ]
                ).lower()
            ]

        if company_id:
            rows = [row for row in rows if row["company_id"] == str(company_id)]
        if contact_id:
            rows = [row for row in rows if row["contact_id"] == str(contact_id)]
        if product_id:
            rows = [row for row in rows if row["product_id"] == str(product_id)]
        return rows


@pytest.fixture
def session() -> FakeSalesSession:
    return FakeSalesSession()


@pytest.mark.asyncio
async def test_deal_status_contract_matches_exposed_schema(session: FakeSalesSession) -> None:
    assert ALLOWED_DEAL_STATUSES == get_args(DealStatus)

    with pytest.raises(ValueError, match="Invalid deal status"):
        await create_deal(
            session,
            tenant_id="tenant-1",
            name="Hidden archived state",
            company_id="company-1",
            amount=Decimal("125.00"),
            currency="usd",
            stage="new lead",
            status="archived",
        )

    created = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Updatable status contract",
        company_id="company-1",
        amount=Decimal("125.00"),
        currency="usd",
        stage="new lead",
        status="open",
    )

    with pytest.raises(ValueError, match="Invalid deal status"):
        await update_deal(
            session,
            tenant_id="tenant-1",
            deal_id=created.id,
            status="archived",
        )


@pytest.mark.asyncio
async def test_create_and_update_deal_reject_contact_company_mismatch(session: FakeSalesSession) -> None:
    with pytest.raises(ValueError, match="Contact does not belong to the selected company"):
        await create_deal(
            session,
            tenant_id="tenant-1",
            name="Mismatch",
            company_id="company-1",
            contact_id="contact-2",
            amount=Decimal("250.00"),
            currency="usd",
            stage="new lead",
            status="open",
        )

    created = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Qualified opportunity",
        company_id="company-1",
        contact_id="contact-1",
        amount=Decimal("250.00"),
        currency="usd",
        stage="qualified lead",
        status="in progress",
    )

    with pytest.raises(ValueError, match="Contact does not belong to the selected company"):
        await update_deal(
            session,
            tenant_id="tenant-1",
            deal_id=created.id,
            company_id="company-2",
        )


@pytest.mark.asyncio
async def test_delete_deal_flow_removes_existing_deal(session: FakeSalesSession) -> None:
    created = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Disposable deal",
        company_id="company-1",
        amount=Decimal("99.00"),
        currency="usd",
        stage="new lead",
        status="open",
    )

    assert await delete_deal(session, tenant_id="tenant-1", deal_id=created.id) is True
    assert await get_deal_by_id(session, tenant_id="tenant-1", deal_id=created.id) is None
    assert await delete_deal(session, tenant_id="tenant-1", deal_id=created.id) is False


@pytest.mark.asyncio
async def test_create_lead_from_intake_uses_deal_backbone(session: FakeSalesSession) -> None:
    created = await create_lead_from_intake(
        session,
        tenant_id="tenant-1",
        name="Website lead",
        company_id="company-1",
        contact_id="contact-1",
        email="lead@example.com",
        phone="+46 555 010 101",
        amount=Decimal("1500.00"),
        currency="sek",
        source="website",
        notes="Requested a pricing callback",
    )

    assert created.stage == "new lead"
    assert created.status == "open"
    assert created.currency == "SEK"
    assert "Lead source: website" in (created.notes or "")
    assert "Lead email: lead@example.com" in (created.notes or "")
    assert "Lead phone: +46 555 010 101" in (created.notes or "")
    assert "Requested a pricing callback" in (created.notes or "")


@pytest.mark.asyncio
async def test_pipeline_report_returns_stage_counts_in_canonical_order(session: FakeSalesSession) -> None:
    await create_deal(
        session,
        tenant_id="tenant-1",
        name="Lead one",
        company_id="company-1",
        amount=Decimal("10.00"),
        currency="usd",
        stage="new lead",
        status="open",
    )
    await create_deal(
        session,
        tenant_id="tenant-1",
        name="Lead two",
        company_id="company-1",
        amount=Decimal("20.00"),
        currency="usd",
        stage="qualified lead",
        status="in progress",
    )
    await create_deal(
        session,
        tenant_id="tenant-1",
        name="Lead three",
        company_id="company-2",
        amount=Decimal("30.00"),
        currency="usd",
        stage="qualified lead",
        status="in progress",
    )
    await create_deal(
        session,
        tenant_id="tenant-1",
        name="Lead four",
        company_id="company-2",
        amount=Decimal("40.00"),
        currency="usd",
        stage="contract signed",
        status="won",
    )

    report = await get_pipeline_report(session, tenant_id="tenant-1")

    assert [item.stage for item in report.items] == list(ALLOWED_DEAL_STAGES)
    assert report.total == 4
    counts = {item.stage: item.count for item in report.items}
    assert counts["new lead"] == 1
    assert counts["qualified lead"] == 2
    assert counts["contract signed"] == 1
    assert counts["deal not secured"] == 0


@pytest.mark.asyncio
async def test_list_deals_opportunities_view_returns_only_active_revenue_stages(
    session: FakeSalesSession,
) -> None:
    await create_deal(
        session,
        tenant_id="tenant-1",
        name="Fresh inbound lead",
        company_id="company-1",
        amount=Decimal("10.00"),
        currency="usd",
        stage="new lead",
        status="open",
    )
    active_opportunity = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Active estimate",
        company_id="company-1",
        amount=Decimal("20.00"),
        currency="usd",
        stage="estimate sent",
        status="in progress",
    )
    await create_deal(
        session,
        tenant_id="tenant-1",
        name="Won contract",
        company_id="company-2",
        amount=Decimal("30.00"),
        currency="usd",
        stage="contract signed",
        status="won",
    )
    await create_deal(
        session,
        tenant_id="tenant-1",
        name="Lost proposal",
        company_id="company-2",
        amount=Decimal("40.00"),
        currency="usd",
        stage="proposal sent",
        status="lost",
    )

    result = await list_deals(
        session,
        tenant_id="tenant-1",
        view="opportunities",
    )

    assert result.total == 1
    assert [item.id for item in result.items] == [active_opportunity.id]


@pytest.mark.asyncio
async def test_update_deal_follow_up_persists_timestamp_and_note(session: FakeSalesSession) -> None:
    created = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Follow-up target",
        company_id="company-1",
        amount=Decimal("500.00"),
        currency="usd",
        stage="qualified lead",
        status="in progress",
    )

    follow_up_at = datetime(2026, 4, 18, 9, 30, tzinfo=timezone.utc)
    updated = await update_deal_follow_up(
        session,
        tenant_id="tenant-1",
        deal_id=created.id,
        next_follow_up_at=follow_up_at,
        follow_up_note="Send revised commercial terms",
    )

    assert updated.next_follow_up_at == follow_up_at
    assert updated.follow_up_note == "Send revised commercial terms"


@pytest.mark.asyncio
async def test_sales_forecast_report_calculates_weighted_pipeline_and_follow_up_attention(
    session: FakeSalesSession,
) -> None:
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 2, 10, 0, tzinfo=timezone.utc)

    qualified = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Qualified deal",
        company_id="company-1",
        amount=Decimal("100.00"),
        currency="usd",
        stage="qualified lead",
        status="open",
    )
    await update_deal_follow_up(
        session,
        tenant_id="tenant-1",
        deal_id=qualified.id,
        next_follow_up_at=now - timedelta(days=1),
        follow_up_note="Call back tomorrow morning",
    )

    estimate = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Estimate deal",
        company_id="company-1",
        amount=Decimal("200.00"),
        currency="usd",
        stage="estimate sent",
        status="in progress",
    )
    await update_deal_follow_up(
        session,
        tenant_id="tenant-1",
        deal_id=estimate.id,
        next_follow_up_at=now + timedelta(days=2),
        follow_up_note="Confirm procurement timeline",
    )

    won = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Closed won",
        company_id="company-2",
        amount=Decimal("300.00"),
        currency="usd",
        stage="contract signed",
        status="won",
    )
    session.deals[won.id]["closed_at"] = start_of_month

    lost = await create_deal(
        session,
        tenant_id="tenant-1",
        name="Closed lost",
        company_id="company-2",
        amount=Decimal("150.00"),
        currency="usd",
        stage="deal not secured",
        status="lost",
    )
    session.deals[lost.id]["closed_at"] = start_of_month + timedelta(days=1)

    await create_deal(
        session,
        tenant_id="tenant-2",
        name="Outside tenant deal",
        company_id="company-3",
        amount=Decimal("999.00"),
        currency="usd",
        stage="proposal sent",
        status="open",
    )

    report = await get_sales_forecast_report(session, tenant_id="tenant-1")

    assert report.summary.total_open_pipeline_amount == Decimal("300.00")
    assert report.summary.weighted_pipeline_amount == Decimal("145.00")
    assert report.summary.won_amount == Decimal("300.00")
    assert report.summary.lost_amount == Decimal("150.00")
    assert report.summary.deals_won_this_period_count == 1
    assert report.summary.deals_won_this_period_amount == Decimal("300.00")
    assert report.summary.deals_lost_this_period_count == 1
    assert report.summary.deals_lost_this_period_amount == Decimal("150.00")
    assert report.summary.overdue_follow_up_count == 1
    assert report.summary.upcoming_follow_up_count == 1
    assert report.summary.due_today_follow_up_count == 0
    assert report.summary.currencies == ["USD"]

    stage_breakdown = {item.stage: item for item in report.stage_breakdown}
    assert stage_breakdown["qualified lead"].count == 1
    assert stage_breakdown["qualified lead"].weighted_amount == Decimal("25.00")
    assert stage_breakdown["estimate sent"].weighted_amount == Decimal("120.00")

    opportunity_breakdown = {item.stage: item for item in report.opportunity_stage_breakdown}
    assert opportunity_breakdown["qualified lead"].count == 1
    assert opportunity_breakdown["estimate sent"].count == 1

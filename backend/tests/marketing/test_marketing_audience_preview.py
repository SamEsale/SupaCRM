from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Any

import pytest

from app.marketing.service import (
    export_marketing_campaign_audience_preview_csv,
    get_marketing_campaign_audience_preview,
)


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)


class _FakeResult:
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        scalar: Any = None,
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar(self) -> Any:
        return self._scalar


class FakeMarketingAudiencePreviewSession:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.tenant_updated_at = now
        self.smtp_settings = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "from_email": "ops@example.com",
            "smtp_password": "secret",
            "is_enabled": True,
        }
        self.whatsapp_settings: dict[str, Any] = {}
        self.campaigns = {
            "campaign-email": {
                "id": "campaign-email",
                "tenant_id": "tenant-1",
                "name": "Email audience preview",
                "channel": "email",
                "audience_type": "all_contacts",
                "audience_description": "Email-ready contacts",
                "target_company_id": None,
                "target_contact_id": None,
                "subject": "Spring launch",
                "message_body": "Hello from SupaCRM",
                "status": "draft",
                "scheduled_for": None,
                "blocked_reason": None,
                "created_at": now,
                "updated_at": now,
            },
            "campaign-whatsapp": {
                "id": "campaign-whatsapp",
                "tenant_id": "tenant-1",
                "name": "WhatsApp audience preview",
                "channel": "whatsapp",
                "audience_type": "all_contacts",
                "audience_description": "WhatsApp follow-up",
                "target_company_id": None,
                "target_contact_id": None,
                "subject": None,
                "message_body": "Checking in",
                "status": "draft",
                "scheduled_for": None,
                "blocked_reason": None,
                "created_at": now,
                "updated_at": now,
            },
            "campaign-foreign": {
                "id": "campaign-foreign",
                "tenant_id": "tenant-2",
                "name": "Other tenant",
                "channel": "email",
                "audience_type": "all_contacts",
                "audience_description": None,
                "target_company_id": None,
                "target_contact_id": None,
                "subject": "Foreign campaign",
                "message_body": "No access",
                "status": "draft",
                "scheduled_for": None,
                "blocked_reason": None,
                "created_at": now,
                "updated_at": now,
            },
        }
        self.companies = {
            "company-1": {
                "id": "company-1",
                "tenant_id": "tenant-1",
                "name": "Northwind",
                "website": None,
                "email": None,
                "phone": None,
                "industry": None,
                "address": None,
                "vat_number": None,
                "registration_number": None,
                "notes": None,
                "created_at": now,
                "updated_at": now,
            }
        }
        self.contacts = {
            "contact-1": {
                "id": "contact-1",
                "tenant_id": "tenant-1",
                "first_name": "Alicia",
                "last_name": "Andersson",
                "email": "alicia@example.com",
                "phone": "+46700000001",
                "company_id": "company-1",
                "company": "Northwind",
                "job_title": None,
                "notes": None,
                "created_at": datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
            "contact-2": {
                "id": "contact-2",
                "tenant_id": "tenant-1",
                "first_name": "Bjorn",
                "last_name": "Berg",
                "email": "alicia@example.com",
                "phone": "+46700000002",
                "company_id": "company-1",
                "company": "Northwind",
                "job_title": None,
                "notes": None,
                "created_at": datetime(2026, 4, 19, 9, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
            "contact-3": {
                "id": "contact-3",
                "tenant_id": "tenant-1",
                "first_name": "Celine",
                "last_name": "Carlsson",
                "email": None,
                "phone": None,
                "company_id": "company-1",
                "company": "Northwind",
                "job_title": None,
                "notes": None,
                "created_at": datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
            "contact-foreign": {
                "id": "contact-foreign",
                "tenant_id": "tenant-2",
                "first_name": "Outside",
                "last_name": "Tenant",
                "email": "outside@example.com",
                "phone": "+46700009999",
                "company_id": None,
                "company": "Other Co",
                "job_title": None,
                "notes": None,
                "created_at": datetime(2026, 4, 21, 9, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
        }

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "from information_schema.columns" in sql and "table_name = 'tenants'" in sql:
            return _FakeResult(
                scalar=str(payload["column_name"]) in {"whatsapp_settings", "smtp_settings"}
            )

        if "from information_schema.tables" in sql and "table_name = :table_name" in sql:
            return _FakeResult(
                scalar=str(payload["table_name"]) in {"marketing_campaigns", "tenants"}
            )

        if "select id, updated_at, whatsapp_settings, smtp_settings from public.tenants" in sql:
            return _FakeResult(
                rows=[
                    {
                        "id": "tenant-1",
                        "updated_at": self.tenant_updated_at,
                        "whatsapp_settings": dict(self.whatsapp_settings),
                        "smtp_settings": dict(self.smtp_settings),
                    }
                ]
            )

        if (
            "select id, tenant_id, name, channel, audience_type, audience_description, target_company_id"
            in sql
            and "from public.marketing_campaigns" in sql
            and "id = cast(:campaign_id as varchar)" in sql
        ):
            campaign = self.campaigns.get(str(payload["campaign_id"]))
            if not campaign or campaign["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(campaign)])

        if (
            "from public.contacts" in sql
            and "where tenant_id = cast(:tenant_id as varchar)" in sql
            and "order by created_at desc, id desc" in sql
        ):
            rows = [
                dict(row)
                for row in self.contacts.values()
                if row["tenant_id"] == str(payload["tenant_id"])
            ]
            if payload.get("contact_id"):
                rows = [row for row in rows if row["id"] == str(payload["contact_id"])]
            if payload.get("company_id"):
                rows = [row for row in rows if row["company_id"] == str(payload["company_id"])]
            rows.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
            return _FakeResult(rows=rows)

        if "from public.contacts" in sql and "id = cast(:contact_id as varchar)" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            if not contact or contact["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(contact)])

        if "from public.companies" in sql and "id = cast(:company_id as varchar)" in sql:
            company = self.companies.get(str(payload["company_id"]))
            if not company or company["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(company)])

        raise AssertionError(f"Unhandled SQL in FakeMarketingAudiencePreviewSession: {sql}")


@pytest.fixture
def session() -> FakeMarketingAudiencePreviewSession:
    return FakeMarketingAudiencePreviewSession()


@pytest.mark.asyncio
async def test_audience_preview_is_tenant_scoped_and_counts_email_eligibility(
    session: FakeMarketingAudiencePreviewSession,
) -> None:
    preview = await get_marketing_campaign_audience_preview(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-email",
        sample_limit=10,
    )

    statuses = {recipient.contact_id: recipient.eligibility_status for recipient in preview.recipients}

    assert preview.total_matched_records == 3
    assert preview.eligible_recipients == 1
    assert preview.excluded_recipients == 2
    assert preview.has_more_recipients is False
    assert [(item.reason, item.count) for item in preview.exclusion_counts] == [
        ("missing_email", 1),
        ("duplicate_contact_method", 1),
    ]
    assert statuses == {
        "contact-1": "eligible",
        "contact-2": "duplicate_contact_method",
        "contact-3": "missing_email",
    }


@pytest.mark.asyncio
async def test_audience_preview_counts_missing_phone_for_whatsapp_channel(
    session: FakeMarketingAudiencePreviewSession,
) -> None:
    preview = await get_marketing_campaign_audience_preview(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-whatsapp",
        sample_limit=10,
    )

    statuses = {recipient.contact_id: recipient.eligibility_status for recipient in preview.recipients}

    assert preview.total_matched_records == 3
    assert preview.eligible_recipients == 2
    assert preview.excluded_recipients == 1
    assert [(item.reason, item.count) for item in preview.exclusion_counts] == [
        ("missing_phone", 1),
    ]
    assert statuses["contact-3"] == "missing_phone"
    assert "Only email campaigns have an execution foundation in this slice." in preview.send_readiness.blocked_reasons


@pytest.mark.asyncio
async def test_audience_preview_export_returns_classified_csv_rows(
    session: FakeMarketingAudiencePreviewSession,
) -> None:
    csv_text, row_count = await export_marketing_campaign_audience_preview_csv(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-email",
    )

    rows = list(csv.DictReader(StringIO(csv_text)))

    assert row_count == 3
    assert [row["contact_name"] for row in rows] == [
        "Alicia Andersson",
        "Bjorn Berg",
        "Celine Carlsson",
    ]
    assert [row["eligibility_status"] for row in rows] == [
        "eligible",
        "duplicate_contact_method",
        "missing_email",
    ]
    assert all(row["email"] != "outside@example.com" for row in rows)
    assert rows[1]["exclusion_reason"] == "Duplicate contact method in this campaign preview."


@pytest.mark.asyncio
async def test_audience_preview_rejects_cross_tenant_campaign_access(
    session: FakeMarketingAudiencePreviewSession,
) -> None:
    with pytest.raises(ValueError, match="Campaign does not exist"):
        await get_marketing_campaign_audience_preview(
            session,
            tenant_id="tenant-1",
            campaign_id="campaign-foreign",
        )

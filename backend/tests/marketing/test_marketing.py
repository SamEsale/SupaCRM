from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from app.crm.service import CompanyDetails, ContactDetails
from app.marketing import service as marketing_service
from app.marketing.service import (
    create_marketing_campaign,
    create_whatsapp_lead_intake,
    get_marketing_integrations,
    list_marketing_campaigns,
    update_marketing_campaign,
    update_smtp_settings,
    update_whatsapp_settings,
)
from app.sales.service import DealDetails


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return self._rows


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

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise AssertionError("Expected scalar value")
        return self._scalar


class FakeMarketingSession:
    def __init__(self) -> None:
        self.tenant_updated_at = datetime.now(timezone.utc)
        self.whatsapp_settings: dict[str, Any] = {
            "business_account_id": "wa-acc-1",
            "display_name": "SupaCRM Inbox",
            "is_enabled": True,
        }
        self.smtp_settings: dict[str, Any] = {}
        self.campaigns: dict[str, dict[str, Any]] = {}

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "from information_schema.columns" in sql and "table_name = 'tenants'" in sql:
            return _FakeResult(
                scalar=str(payload["column_name"])
                in {"whatsapp_settings", "smtp_settings"}
            )

        if (
            "from information_schema.tables" in sql
            and "table_name = :table_name" in sql
        ):
            return _FakeResult(
                scalar=str(payload["table_name"]) == "marketing_campaigns"
            )

        if (
            "select id, updated_at, whatsapp_settings, smtp_settings from public.tenants"
            in sql
        ):
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
            "select updated_at, whatsapp_settings, smtp_settings from public.tenants"
            in sql
        ):
            return _FakeResult(
                rows=[
                    {
                        "updated_at": self.tenant_updated_at,
                        "whatsapp_settings": dict(self.whatsapp_settings),
                        "smtp_settings": dict(self.smtp_settings),
                    }
                ]
            )

        if "select whatsapp_settings from public.tenants" in sql:
            return _FakeResult(
                rows=[{"whatsapp_settings": dict(self.whatsapp_settings)}]
            )

        if "select smtp_settings from public.tenants" in sql:
            return _FakeResult(rows=[{"smtp_settings": dict(self.smtp_settings)}])

        if "update public.tenants set whatsapp_settings" in sql:
            self.whatsapp_settings = (
                dict(payload["whatsapp_settings"])
                if isinstance(payload["whatsapp_settings"], dict)
                else __import__("json").loads(str(payload["whatsapp_settings"]))
            )
            self.tenant_updated_at = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        if "update public.tenants set smtp_settings" in sql:
            self.smtp_settings = (
                dict(payload["smtp_settings"])
                if isinstance(payload["smtp_settings"], dict)
                else __import__("json").loads(str(payload["smtp_settings"]))
            )
            self.tenant_updated_at = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        if "select count(*) from public.marketing_campaigns" in sql:
            return _FakeResult(scalar=len(self._filter_campaigns(payload)))

        if (
            "select id, tenant_id, name, channel, audience_type, audience_description, target_company_id"
            in sql
            and "from public.marketing_campaigns" in sql
            and "where tenant_id = cast(:tenant_id as varchar) and id = cast(:campaign_id as varchar)"
            in sql
        ):
            campaign = self.campaigns.get(str(payload["campaign_id"]))
            if not campaign or campaign["tenant_id"] != str(payload["tenant_id"]):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[dict(campaign)])

        if (
            "from public.marketing_campaigns" in sql
            and "order by updated_at desc" in sql
        ):
            rows = self._filter_campaigns(payload)
            rows.sort(key=lambda row: (row["updated_at"], row["id"]), reverse=True)
            return _FakeResult(rows=[dict(row) for row in rows])

        if "insert into public.marketing_campaigns" in sql:
            now = datetime.now(timezone.utc)
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "name": str(payload["name"]),
                "channel": str(payload["channel"]),
                "audience_type": str(payload["audience_type"]),
                "audience_description": payload.get("audience_description"),
                "target_company_id": payload.get("target_company_id"),
                "target_contact_id": payload.get("target_contact_id"),
                "subject": payload.get("subject"),
                "message_body": str(payload["message_body"]),
                "status": str(payload["status"]),
                "scheduled_for": payload.get("scheduled_for"),
                "blocked_reason": payload.get("blocked_reason"),
                "created_at": now,
                "updated_at": now,
            }
            self.campaigns[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "update public.marketing_campaigns set" in sql:
            campaign = self.campaigns.get(str(payload["campaign_id"]))
            if not campaign:
                return _FakeResult(rows=[])
            campaign.update(
                {
                    "name": str(payload["name"]),
                    "channel": str(payload["channel"]),
                    "audience_type": str(payload["audience_type"]),
                    "audience_description": payload.get("audience_description"),
                    "target_company_id": payload.get("target_company_id"),
                    "target_contact_id": payload.get("target_contact_id"),
                    "subject": payload.get("subject"),
                    "message_body": str(payload["message_body"]),
                    "status": str(payload["status"]),
                    "scheduled_for": payload.get("scheduled_for"),
                    "blocked_reason": payload.get("blocked_reason"),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            return _FakeResult(rows=[dict(campaign)])

        if (
            "from public.companies" in sql
            and "lower(name) = lower(cast(:name as varchar))" in sql
        ):
            return _FakeResult(rows=[])

        if "from public.contacts" in sql and "phone = cast(:phone as varchar)" in sql:
            return _FakeResult(rows=[])

        raise AssertionError(f"Unhandled SQL in FakeMarketingSession: {sql}")

    def _filter_campaigns(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = [
            dict(row)
            for row in self.campaigns.values()
            if row["tenant_id"] == str(payload["tenant_id"])
        ]
        search = str(payload.get("search", "")).replace("%", "").lower()
        if search:
            rows = [
                row
                for row in rows
                if search
                in " ".join(
                    [
                        row["name"],
                        str(row.get("audience_description") or ""),
                        str(row.get("subject") or ""),
                        row["message_body"],
                    ]
                ).lower()
            ]
        if payload.get("channel"):
            rows = [row for row in rows if row["channel"] == str(payload["channel"])]
        if payload.get("status"):
            rows = [row for row in rows if row["status"] == str(payload["status"])]
        return rows


@pytest.fixture
def session() -> FakeMarketingSession:
    return FakeMarketingSession()


@pytest.mark.asyncio
async def test_marketing_settings_persist_sender_identity(
    session: FakeMarketingSession,
) -> None:
    smtp = await update_smtp_settings(
        session,
        tenant_id="tenant-1",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="mailer",
        smtp_password="secret",
        from_email="no-reply@example.com",
        from_name="Growth Team",
        use_tls=True,
        use_ssl=False,
        is_enabled=True,
    )
    whatsapp = await update_whatsapp_settings(
        session,
        tenant_id="tenant-1",
        business_account_id="wa-acc-2",
        phone_number_id="pn-1",
        display_name="SupaCRM Social",
        access_token="new-token",
        webhook_verify_token="verify-me",
        is_enabled=True,
    )
    integrations = await get_marketing_integrations(session, tenant_id="tenant-1")

    assert smtp.from_name == "Growth Team"
    assert smtp.password_set is True
    assert whatsapp.access_token_set is True
    assert integrations.smtp.from_name == "Growth Team"
    assert integrations.whatsapp.display_name == "SupaCRM Social"


@pytest.mark.asyncio
async def test_campaign_draft_create_update_and_list(
    session: FakeMarketingSession,
) -> None:
    created = await create_marketing_campaign(
        session,
        tenant_id="tenant-1",
        name="Spring outreach",
        channel="email",
        audience_type="all_contacts",
        audience_description="Qualified opportunities",
        target_company_id=None,
        target_contact_id=None,
        subject="Spring launch",
        message_body="Hello from SupaCRM",
        status="draft",
        scheduled_for=None,
    )

    with pytest.raises(
        ValueError, match="Scheduled campaigns require a scheduled time"
    ):
        await create_marketing_campaign(
            session,
            tenant_id="tenant-1",
            name="Broken schedule",
            channel="whatsapp",
            audience_type="all_contacts",
            audience_description=None,
            target_company_id=None,
            target_contact_id=None,
            subject=None,
            message_body="Follow up",
            status="scheduled",
            scheduled_for=None,
        )

    scheduled_for = datetime.now(timezone.utc)
    updated = await update_marketing_campaign(
        session,
        tenant_id="tenant-1",
        campaign_id=created.id,
        name="Spring outreach",
        channel="email",
        audience_type="all_contacts",
        audience_description="Qualified opportunities",
        target_company_id=None,
        target_contact_id=None,
        subject="Spring launch",
        message_body="Hello from SupaCRM",
        status="scheduled",
        scheduled_for=scheduled_for,
    )
    listed = await list_marketing_campaigns(
        session, tenant_id="tenant-1", status="scheduled"
    )

    assert created.status == "draft"
    assert updated.status == "scheduled"
    assert updated.scheduled_for == scheduled_for
    assert listed.total == 1
    assert listed.items[0].id == created.id


@pytest.mark.asyncio
async def test_whatsapp_intake_maps_into_company_contact_and_deal(
    session: FakeMarketingSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = await create_marketing_campaign(
        session,
        tenant_id="tenant-1",
        name="WhatsApp revive",
        channel="whatsapp",
        audience_type="all_contacts",
        audience_description="Dormant buyers",
        target_company_id=None,
        target_contact_id=None,
        subject=None,
        message_body="Checking in with past interest",
        status="draft",
        scheduled_for=None,
    )

    captured: dict[str, Any] = {}

    async def _fake_create_company(*_: Any, **kwargs: Any) -> CompanyDetails:
        captured["company"] = kwargs
        return CompanyDetails(
            id="company-new",
            tenant_id="tenant-1",
            name="Nordic Buyer",
            website=None,
            email=None,
            phone="+46700000000",
            industry=None,
            address=None,
            vat_number=None,
            registration_number=None,
            notes=kwargs.get("notes"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _fake_create_contact(*_: Any, **kwargs: Any) -> ContactDetails:
        captured["contact"] = kwargs
        return ContactDetails(
            id="contact-new",
            tenant_id="tenant-1",
            first_name="Alicia Andersson",
            last_name=None,
            email=kwargs.get("email"),
            phone=kwargs.get("phone"),
            company_id="company-new",
            company="Nordic Buyer",
            job_title=None,
            notes=kwargs.get("notes"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _fake_create_deal(*_: Any, **kwargs: Any) -> DealDetails:
        captured["deal"] = kwargs
        return DealDetails(
            id="deal-new",
            tenant_id="tenant-1",
            name=kwargs["name"],
            company_id=kwargs["company_id"],
            contact_id=kwargs["contact_id"],
            product_id=None,
            amount=Decimal(str(kwargs["amount"])),
            currency=kwargs["currency"],
            stage=kwargs["stage"],
            status=kwargs["status"],
            expected_close_date=None,
            notes=kwargs.get("notes"),
            next_follow_up_at=None,
            follow_up_note=None,
            closed_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(marketing_service, "create_company", _fake_create_company)
    monkeypatch.setattr(marketing_service, "create_contact", _fake_create_contact)
    monkeypatch.setattr(marketing_service, "create_deal", _fake_create_deal)

    result = await create_whatsapp_lead_intake(
        session,
        tenant_id="tenant-1",
        sender_name="Alicia Andersson",
        sender_phone="+46700000000",
        message_text="Can you send pricing for the spring package?",
        message_type="text",
        received_at=datetime.now(timezone.utc),
        company_id=None,
        company_name="Nordic Buyer",
        contact_id=None,
        email="alicia@example.com",
        amount="1250.00",
        currency="eur",
        campaign_id=campaign.id,
        notes="Prefers WhatsApp over email",
        whatsapp_account_id=None,
    )

    assert result.deal.id == "deal-new"
    assert result.company.id == "company-new"
    assert result.contact is not None and result.contact.id == "contact-new"
    assert result.campaign is not None and result.campaign.id == campaign.id
    assert captured["deal"]["stage"] == "new lead"
    assert captured["deal"]["status"] == "open"
    assert captured["deal"]["currency"] == "EUR"
    assert "Created from inbound WhatsApp message." in captured["deal"]["notes"]
    assert "Campaign: WhatsApp revive" in captured["deal"]["notes"]
    assert "Lead email: alicia@example.com" in captured["deal"]["notes"]


@pytest.mark.asyncio
async def test_whatsapp_intake_surfaces_deal_constraint_mismatch_as_validation_error(
    session: FakeMarketingSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_create_company(*_: Any, **kwargs: Any) -> CompanyDetails:
        return CompanyDetails(
            id="company-new",
            tenant_id="tenant-1",
            name=str(kwargs["name"]),
            website=None,
            email=None,
            phone=kwargs.get("phone"),
            industry=None,
            address=None,
            vat_number=None,
            registration_number=None,
            notes=kwargs.get("notes"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _fake_create_contact(*_: Any, **kwargs: Any) -> ContactDetails:
        return ContactDetails(
            id="contact-new",
            tenant_id="tenant-1",
            first_name=str(kwargs["first_name"]),
            last_name=kwargs.get("last_name"),
            email=kwargs.get("email"),
            phone=kwargs.get("phone"),
            company_id=str(kwargs["company_id"]),
            company=str(kwargs["company"]),
            job_title=kwargs.get("job_title"),
            notes=kwargs.get("notes"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _fake_create_deal(*_: Any, **__: Any) -> DealDetails:
        raise IntegrityError(
            "insert into public.deals (...)",
            {},
            Exception(
                'new row for relation "deals" violates check constraint "ck_deals_stage_valid"'
            ),
        )

    monkeypatch.setattr(marketing_service, "create_company", _fake_create_company)
    monkeypatch.setattr(marketing_service, "create_contact", _fake_create_contact)
    monkeypatch.setattr(marketing_service, "create_deal", _fake_create_deal)

    with pytest.raises(
        ValueError,
        match="sales stage/status contract is out of sync with persistence constraints",
    ):
        await create_whatsapp_lead_intake(
            session,
            tenant_id="tenant-1",
            sender_name="Alicia Andersson",
            sender_phone="+46700000000",
            message_text="Can you send pricing?",
            message_type="text",
            received_at=datetime.now(timezone.utc),
            company_id=None,
            company_name="Nordic Buyer",
            contact_id=None,
            email="alicia@example.com",
            amount="0",
            currency="USD",
            campaign_id=None,
            notes="Manual intake",
            whatsapp_account_id=None,
        )

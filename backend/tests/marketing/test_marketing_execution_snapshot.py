from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from typing import Any

import pytest

from app.marketing import service as marketing_service
from app.marketing.service import (
    create_failed_execution_recipient_follow_up_handoff,
    export_marketing_campaign_execution_results_csv,
    get_marketing_campaign_detail,
    get_marketing_campaign_execution_readback,
    list_marketing_campaign_executions,
    process_email_campaign_execution,
    start_email_campaign_execution,
)


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)


class _FakeResult:
    def __init__(self, *, rows: list[dict[str, Any]] | None = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar(self) -> Any:
        return self._scalar


class FakeMarketingExecutionSession:
    def __init__(self, *, smtp_enabled: bool = True) -> None:
        now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        self.tenant_updated_at = now
        self.smtp_settings: dict[str, Any] = (
            {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_username": "mailer",
                "smtp_password": "secret",
                "from_email": "ops@example.com",
                "use_tls": True,
                "use_ssl": False,
                "is_enabled": True,
            }
            if smtp_enabled
            else {}
        )
        self.whatsapp_settings: dict[str, Any] = {}
        self.campaigns = {
            "campaign-1": {
                "id": "campaign-1",
                "tenant_id": "tenant-1",
                "name": "Spring launch",
                "channel": "email",
                "audience_type": "all_contacts",
                "audience_description": "Qualified contacts",
                "target_company_id": None,
                "target_contact_id": None,
                "subject": "Launch update",
                "message_body": "Hello from SupaCRM",
                "status": "draft",
                "scheduled_for": None,
                "blocked_reason": None,
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
                "phone": "+46700000000",
                "company_id": None,
                "company": "Northwind",
                "job_title": None,
                "notes": None,
                "created_at": datetime(2026, 4, 21, 9, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
            "contact-2": {
                "id": "contact-2",
                "tenant_id": "tenant-1",
                "first_name": "Bjorn",
                "last_name": "Berg",
                "email": "alicia@example.com",
                "phone": "+46700000001",
                "company_id": None,
                "company": "Northwind",
                "job_title": None,
                "notes": None,
                "created_at": datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
            "contact-3": {
                "id": "contact-3",
                "tenant_id": "tenant-1",
                "first_name": "Celine",
                "last_name": "Carlsson",
                "email": None,
                "phone": "+46700000002",
                "company_id": None,
                "company": "Northwind",
                "job_title": None,
                "notes": None,
                "created_at": datetime(2026, 4, 19, 9, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
            "contact-foreign": {
                "id": "contact-foreign",
                "tenant_id": "tenant-2",
                "first_name": "Outside",
                "last_name": "Tenant",
                "email": "outside@example.com",
                "phone": "+46709999999",
                "company_id": None,
                "company": "Other Co",
                "job_title": None,
                "notes": None,
                "created_at": datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
        }
        self.executions: dict[str, dict[str, Any]] = {}
        self.execution_recipients: dict[str, dict[str, Any]] = {}

    def store_execution(
        self,
        *,
        execution_id: str,
        tenant_id: str,
        campaign_id: str,
        status: str,
        requested_at: datetime,
        created_at: datetime | None = None,
        total_recipients: int = 0,
        processed_recipients: int = 0,
        sent_recipients: int = 0,
        failed_recipients: int = 0,
        queue_job_id: str | None = None,
        blocked_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        created = created_at or requested_at
        self.executions[execution_id] = {
            "id": execution_id,
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "channel": "email",
            "status": status,
            "total_recipients": total_recipients,
            "processed_recipients": processed_recipients,
            "sent_recipients": sent_recipients,
            "failed_recipients": failed_recipients,
            "batch_size": 100,
            "queued_batch_count": 1 if total_recipients else 0,
            "queue_job_id": queue_job_id,
            "blocked_reason": blocked_reason,
            "metadata": metadata or {},
            "requested_at": requested_at,
            "started_at": started_at,
            "completed_at": completed_at,
            "created_at": created,
            "updated_at": updated_at or created,
        }

    def store_execution_recipient(
        self,
        *,
        recipient_id: str,
        execution_id: str,
        campaign_id: str,
        tenant_id: str,
        email: str,
        phone: str | None,
        first_name: str,
        last_name: str | None,
        company: str | None,
        status: str,
        batch_number: int = 1,
        failure_reason: str | None = None,
        sent_at: datetime | None = None,
        support_ticket_id: str | None = None,
        handoff_at: datetime | None = None,
        handoff_by_user_id: str | None = None,
        handoff_status: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.execution_recipients[recipient_id] = {
            "id": recipient_id,
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "campaign_id": campaign_id,
            "contact_id": None,
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "batch_number": batch_number,
            "status": status,
            "failure_reason": failure_reason,
            "support_ticket_id": support_ticket_id,
            "handoff_at": handoff_at,
            "handoff_by_user_id": handoff_by_user_id,
            "handoff_status": handoff_status,
            "sent_at": sent_at,
            "created_at": now,
            "updated_at": now,
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
                scalar=str(payload["table_name"])
                in {
                    "marketing_campaigns",
                    "marketing_campaign_executions",
                    "marketing_campaign_execution_recipients",
                }
            )

        if (
            "select id, updated_at, whatsapp_settings, smtp_settings from public.tenants" in sql
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

        if "select smtp_settings from public.tenants" in sql:
            return _FakeResult(rows=[{"smtp_settings": dict(self.smtp_settings)}])

        if (
            "from public.marketing_campaigns" in sql
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
            rows.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
            return _FakeResult(rows=rows)

        if (
            "from public.marketing_campaign_executions" in sql
            and "campaign_id = cast(:campaign_id as varchar)" in sql
            and "order by requested_at desc, created_at desc, id desc" in sql
        ):
            rows = [
                dict(row)
                for row in self.executions.values()
                if row["tenant_id"] == str(payload["tenant_id"])
                and row["campaign_id"] == str(payload["campaign_id"])
            ]
            rows.sort(key=lambda row: (row["requested_at"], row["created_at"], row["id"]), reverse=True)
            if "limit :limit" in sql:
                rows = rows[: int(payload["limit"])]
            return _FakeResult(rows=rows)

        if (
            "from public.marketing_campaign_executions" in sql
            and "where id = cast(:execution_id as varchar)" in sql
        ):
            execution = self.executions.get(str(payload["execution_id"]))
            if execution and payload.get("tenant_id") and execution["tenant_id"] != str(payload["tenant_id"]):
                execution = None
            if execution and payload.get("campaign_id") and execution["campaign_id"] != str(payload["campaign_id"]):
                execution = None
            return _FakeResult(rows=[dict(execution)] if execution else [])

        if "insert into public.marketing_campaign_executions" in sql:
            now = datetime.now(timezone.utc)
            metadata = payload.get("metadata")
            parsed_metadata = (
                json.loads(str(metadata)) if isinstance(metadata, str) and metadata else {}
            )
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "campaign_id": str(payload["campaign_id"]),
                "channel": str(payload["channel"]),
                "status": str(payload["status"]),
                "total_recipients": int(payload["total_recipients"]),
                "processed_recipients": 0,
                "sent_recipients": 0,
                "failed_recipients": 0,
                "batch_size": int(payload["batch_size"]),
                "queued_batch_count": int(payload["queued_batch_count"]),
                "queue_job_id": None,
                "blocked_reason": payload.get("blocked_reason"),
                "metadata": parsed_metadata,
                "requested_at": now,
                "started_at": now if payload["status"] == "sending" else None,
                "completed_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self.executions[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "update public.marketing_campaign_executions set queue_job_id" in sql:
            execution = self.executions[str(payload["execution_id"])]
            execution["queue_job_id"] = payload["queue_job_id"]
            execution["updated_at"] = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        if (
            "update public.marketing_campaign_executions" in sql
            and "processed_recipients = :processed_recipients" in sql
        ):
            execution = self.executions[str(payload["execution_id"])]
            execution["status"] = str(payload["status"])
            execution["processed_recipients"] = int(payload["processed_recipients"])
            execution["sent_recipients"] = int(payload["sent_recipients"])
            execution["failed_recipients"] = int(payload["failed_recipients"])
            execution["blocked_reason"] = payload.get("blocked_reason")
            if payload.get("mark_started"):
                execution["started_at"] = execution["started_at"] or datetime.now(timezone.utc)
            if payload.get("mark_completed"):
                execution["completed_at"] = datetime.now(timezone.utc)
            execution["updated_at"] = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        if "insert into public.marketing_campaign_execution_recipients" in sql:
            now = datetime.now(timezone.utc)
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "execution_id": str(payload["execution_id"]),
                "campaign_id": str(payload["campaign_id"]),
                "contact_id": str(payload["contact_id"]),
                "email": str(payload["email"]),
                "phone": payload.get("phone"),
                "first_name": payload.get("first_name"),
                "last_name": payload.get("last_name"),
                "company": payload.get("company"),
                "batch_number": int(payload["batch_number"]),
                "status": "pending",
                "failure_reason": None,
                "support_ticket_id": None,
                "handoff_at": None,
                "handoff_by_user_id": None,
                "handoff_status": None,
                "sent_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self.execution_recipients[row["id"]] = row
            return _FakeResult(rows=[])

        if (
            "from public.marketing_campaign_execution_recipients" in sql
            and "execution_id = cast(:execution_id as varchar)" in sql
        ):
            rows = [
                dict(row)
                for row in self.execution_recipients.values()
                if row["tenant_id"] == str(payload["tenant_id"])
                and row["execution_id"] == str(payload["execution_id"])
            ]
            rows.sort(key=lambda row: (row["batch_number"], row["email"]))
            if "limit :limit" in sql:
                rows = rows[: int(payload["limit"])]
            return _FakeResult(rows=rows)

        if "update public.marketing_campaign_execution_recipients set status = 'sent'" in sql:
            recipient = self.execution_recipients[str(payload["recipient_id"])]
            recipient["status"] = "sent"
            recipient["failure_reason"] = None
            recipient["sent_at"] = datetime.now(timezone.utc)
            recipient["updated_at"] = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        if (
            "update public.marketing_campaign_execution_recipients" in sql
            and "set support_ticket_id = cast(:support_ticket_id as varchar)" in sql
        ):
            recipient = self.execution_recipients[str(payload["recipient_id"])]
            recipient["support_ticket_id"] = str(payload["support_ticket_id"])
            recipient["handoff_at"] = datetime.now(timezone.utc)
            recipient["handoff_by_user_id"] = (
                str(payload["handoff_by_user_id"])
                if payload.get("handoff_by_user_id")
                else None
            )
            recipient["handoff_status"] = "created"
            recipient["updated_at"] = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        if (
            "update public.marketing_campaign_execution_recipients" in sql
            and "set handoff_at = now()" in sql
            and "handoff_status = 'failed'" in sql
        ):
            recipient = self.execution_recipients[str(payload["recipient_id"])]
            recipient["handoff_at"] = datetime.now(timezone.utc)
            recipient["handoff_by_user_id"] = (
                str(payload["handoff_by_user_id"])
                if payload.get("handoff_by_user_id")
                else None
            )
            recipient["handoff_status"] = "failed"
            recipient["updated_at"] = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        if "update public.marketing_campaign_execution_recipients set status = 'failed'" in sql:
            if "and execution_id = cast(:execution_id as varchar)" in sql:
                for recipient in self.execution_recipients.values():
                    if (
                        recipient["tenant_id"] == str(payload["tenant_id"])
                        and recipient["execution_id"] == str(payload["execution_id"])
                        and recipient["status"] == "pending"
                    ):
                        recipient["status"] = "failed"
                        recipient["failure_reason"] = str(payload["failure_reason"])
                        recipient["updated_at"] = datetime.now(timezone.utc)
                return _FakeResult(rows=[])
            recipient = self.execution_recipients[str(payload["recipient_id"])]
            recipient["status"] = "failed"
            recipient["failure_reason"] = str(payload["failure_reason"])
            recipient["updated_at"] = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        if "update public.marketing_campaigns set status = cast(:status as varchar)" in sql:
            campaign = self.campaigns[str(payload["campaign_id"])]
            campaign["status"] = str(payload["status"])
            campaign["blocked_reason"] = payload.get("blocked_reason")
            campaign["updated_at"] = datetime.now(timezone.utc)
            return _FakeResult(rows=[])

        raise AssertionError(f"Unhandled SQL in FakeMarketingExecutionSession: {sql}")


@pytest.fixture
def session() -> FakeMarketingExecutionSession:
    return FakeMarketingExecutionSession()


@pytest.mark.asyncio
async def test_start_email_campaign_execution_freezes_snapshot_and_latest_detail(
    session: FakeMarketingExecutionSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        marketing_service,
        "enqueue_marketing_campaign_execution",
        lambda **_: "job-1",
    )

    detail = await start_email_campaign_execution(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        initiated_by_user_id="user-1",
    )

    assert detail.campaign.status == "sending"
    assert detail.latest_execution is not None
    assert detail.latest_execution.status == "queued"
    assert detail.latest_execution.started_at is None
    assert detail.latest_execution.queue_job_id == "job-1"
    assert detail.latest_execution.total_recipients == 1
    assert detail.latest_execution_snapshot is not None
    assert detail.latest_execution_snapshot.total_matched_records == 3
    assert detail.latest_execution_snapshot.eligible_recipients == 1
    assert detail.latest_execution_snapshot.excluded_recipients == 2
    assert [(item.reason, item.count) for item in detail.latest_execution_snapshot.exclusion_counts] == [
        ("missing_email", 1),
        ("duplicate_contact_method", 1),
    ]
    assert [recipient.email for recipient in detail.recent_recipients] == ["alicia@example.com"]
    assert detail.execution_history[0].id == detail.latest_execution.id
    assert detail.recent_recipients[0].phone == "+46700000000"

    stored_execution = next(iter(session.executions.values()))
    assert stored_execution["metadata"]["audience_snapshot"]["eligible_recipients"] == 1
    assert len(session.execution_recipients) == 1


@pytest.mark.asyncio
async def test_start_email_campaign_execution_rejects_blocked_send_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeMarketingExecutionSession(smtp_enabled=False)
    monkeypatch.setattr(
        marketing_service,
        "enqueue_marketing_campaign_execution",
        lambda **_: "job-1",
    )

    with pytest.raises(ValueError, match="SMTP must be configured and enabled before email campaigns can send"):
        await start_email_campaign_execution(
            session,
            tenant_id="tenant-1",
            campaign_id="campaign-1",
            initiated_by_user_id="user-1",
        )

    assert session.executions == {}
    assert session.campaigns["campaign-1"]["status"] == "draft"


@pytest.mark.asyncio
async def test_process_email_campaign_execution_uses_frozen_execution_recipients(
    session: FakeMarketingExecutionSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        marketing_service,
        "enqueue_marketing_campaign_execution",
        lambda **_: "job-1",
    )

    detail = await start_email_campaign_execution(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        initiated_by_user_id="user-1",
    )
    execution_id = detail.latest_execution.id if detail.latest_execution else ""

    session.contacts["contact-1"]["email"] = "changed@example.com"
    session.contacts["contact-4"] = {
        "id": "contact-4",
        "tenant_id": "tenant-1",
        "first_name": "Dana",
        "last_name": "Dahl",
        "email": "dana@example.com",
        "phone": "+46700000003",
        "company_id": None,
        "company": "Northwind",
        "job_title": None,
        "notes": None,
        "created_at": datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    sent_to: list[str] = []

    async def _fake_send(message, **_: Any) -> None:
        sent_to.append(str(message["To"]))

    monkeypatch.setattr(marketing_service.aiosmtplib, "send", _fake_send)

    await process_email_campaign_execution(session, execution_id=execution_id)

    assert sent_to == ["alicia@example.com"]
    detail_after = await get_marketing_campaign_detail(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
    )
    assert detail_after.latest_execution is not None
    assert detail_after.latest_execution.status == "completed"
    assert detail_after.latest_execution.started_at is not None
    assert detail_after.latest_execution.sent_recipients == 1
    assert detail_after.execution_history[0].id == execution_id
    assert detail_after.recent_recipients[0].status == "sent"


@pytest.mark.asyncio
async def test_process_email_campaign_execution_tracks_recipient_failures(
    session: FakeMarketingExecutionSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session.contacts["contact-2"]["email"] = "bjorn@example.com"
    monkeypatch.setattr(
        marketing_service,
        "enqueue_marketing_campaign_execution",
        lambda **_: "job-1",
    )

    detail = await start_email_campaign_execution(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        initiated_by_user_id="user-1",
    )
    execution_id = detail.latest_execution.id if detail.latest_execution else ""

    async def _fake_send(message, **_: Any) -> None:
        if str(message["To"]) == "bjorn@example.com":
            raise RuntimeError("SMTP recipient rejected")

    monkeypatch.setattr(marketing_service.aiosmtplib, "send", _fake_send)

    await process_email_campaign_execution(session, execution_id=execution_id)

    detail_after = await get_marketing_campaign_detail(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
    )
    assert detail_after.latest_execution is not None
    assert detail_after.latest_execution.status == "failed"
    assert detail_after.latest_execution.processed_recipients == 2
    assert detail_after.latest_execution.sent_recipients == 1
    assert detail_after.latest_execution.failed_recipients == 1
    assert detail_after.latest_execution.blocked_reason == "Some recipients failed during SMTP dispatch."
    recipient_statuses = {recipient.email: recipient.status for recipient in detail_after.recent_recipients}
    assert recipient_statuses["alicia@example.com"] == "sent"
    assert recipient_statuses["bjorn@example.com"] == "failed"


@pytest.mark.asyncio
async def test_campaign_detail_returns_execution_history_in_descending_requested_order() -> None:
    session = FakeMarketingExecutionSession()
    earlier = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
    later = datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc)
    session.store_execution(
        execution_id="execution-earlier",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="completed",
        requested_at=earlier,
        total_recipients=1,
        processed_recipients=1,
        sent_recipients=1,
        completed_at=earlier,
        queue_job_id="job-earlier",
    )
    session.store_execution(
        execution_id="execution-later",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="failed",
        requested_at=later,
        total_recipients=2,
        processed_recipients=2,
        sent_recipients=1,
        failed_recipients=1,
        completed_at=later,
        queue_job_id="job-later",
        blocked_reason="One recipient failed.",
    )
    session.store_execution_recipient(
        recipient_id="recipient-later-1",
        execution_id="execution-later",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="alicia@example.com",
        phone="+46700000000",
        first_name="Alicia",
        last_name="Andersson",
        company="Northwind",
        status="sent",
        sent_at=later,
    )
    session.store_execution_recipient(
        recipient_id="recipient-later-2",
        execution_id="execution-later",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="bjorn@example.com",
        phone="+46700000001",
        first_name="Bjorn",
        last_name="Berg",
        company="Northwind",
        status="failed",
        failure_reason="SMTP recipient rejected",
    )

    detail = await get_marketing_campaign_detail(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
    )

    assert [execution.id for execution in detail.execution_history] == [
        "execution-later",
        "execution-earlier",
    ]
    assert detail.latest_execution is not None
    assert detail.latest_execution.id == "execution-later"
    assert [recipient.contact_name for recipient in detail.recent_recipients] == [
        "Alicia Andersson",
        "Bjorn Berg",
    ]


@pytest.mark.asyncio
async def test_execution_readback_enforces_tenant_scoping() -> None:
    session = FakeMarketingExecutionSession()
    session.store_execution(
        execution_id="execution-foreign",
        tenant_id="tenant-2",
        campaign_id="campaign-1",
        status="failed",
        requested_at=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="Campaign execution does not exist"):
        await get_marketing_campaign_execution_readback(
            session,
            tenant_id="tenant-1",
            campaign_id="campaign-1",
            execution_id="execution-foreign",
            recipient_filter="all",
        )


@pytest.mark.asyncio
async def test_execution_readback_filters_failed_recipients() -> None:
    session = FakeMarketingExecutionSession()
    requested_at = datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc)
    session.store_execution(
        execution_id="execution-1",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="failed",
        requested_at=requested_at,
        total_recipients=4,
        processed_recipients=4,
        sent_recipients=1,
        failed_recipients=2,
        blocked_reason="Some recipients failed during SMTP dispatch.",
    )
    session.store_execution_recipient(
        recipient_id="recipient-sent",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="alicia@example.com",
        phone="+46700000000",
        first_name="Alicia",
        last_name="Andersson",
        company="Northwind",
        status="sent",
        sent_at=requested_at,
    )
    session.store_execution_recipient(
        recipient_id="recipient-failed",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="bjorn@example.com",
        phone="+46700000001",
        first_name="Bjorn",
        last_name="Berg",
        company="Northwind",
        status="failed",
        failure_reason="SMTP recipient rejected",
    )
    session.store_execution_recipient(
        recipient_id="recipient-pending",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="celine@example.com",
        phone="+46700000002",
        first_name="Celine",
        last_name="Carlsson",
        company="Northwind",
        status="pending",
    )
    session.store_execution_recipient(
        recipient_id="recipient-blocked",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="dana@example.com",
        phone="+46700000003",
        first_name="Dana",
        last_name="Dahl",
        company="Northwind",
        status="blocked",
        failure_reason="Queue unavailable",
    )

    readback = await get_marketing_campaign_execution_readback(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        execution_id="execution-1",
        recipient_filter="failed",
    )

    assert readback.execution.id == "execution-1"
    assert readback.recipient_filter == "failed"
    assert [recipient.email for recipient in readback.recipients] == ["bjorn@example.com"]
    assert [(item.status, item.count) for item in readback.recipient_counts] == [
        ("all", 4),
        ("failed", 1),
        ("sent", 1),
        ("pending", 1),
        ("blocked", 1),
    ]


@pytest.mark.asyncio
async def test_export_execution_results_csv_uses_persisted_recipient_rows() -> None:
    session = FakeMarketingExecutionSession()
    sent_at = datetime(2026, 4, 21, 8, 15, tzinfo=timezone.utc)
    session.store_execution(
        execution_id="execution-1",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="completed",
        requested_at=sent_at,
        total_recipients=1,
        processed_recipients=1,
        sent_recipients=1,
        completed_at=sent_at,
    )
    session.store_execution_recipient(
        recipient_id="recipient-1",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="alicia@example.com",
        phone="+46700000000",
        first_name="Alicia",
        last_name="Andersson",
        company="Northwind",
        status="sent",
        batch_number=2,
        sent_at=sent_at,
    )

    csv_text, row_count = await export_marketing_campaign_execution_results_csv(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        execution_id="execution-1",
    )
    rows = list(csv.DictReader(StringIO(csv_text)))

    assert row_count == 1
    assert rows == [
        {
            "execution_id": "execution-1",
            "campaign_id": "campaign-1",
            "contact_name": "Alicia Andersson",
            "email": "alicia@example.com",
            "phone": "+46700000000",
            "company": "Northwind",
            "status": "sent",
            "failure_reason": "",
            "support_ticket_id": "",
            "sent_at": sent_at.isoformat(),
            "batch_number": "2",
        }
    ]


@pytest.mark.asyncio
async def test_export_execution_results_csv_supports_failed_only_filter() -> None:
    session = FakeMarketingExecutionSession()
    requested_at = datetime(2026, 4, 21, 8, 15, tzinfo=timezone.utc)
    session.store_execution(
        execution_id="execution-1",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="failed",
        requested_at=requested_at,
        total_recipients=2,
        processed_recipients=2,
        sent_recipients=1,
        failed_recipients=1,
    )
    session.store_execution_recipient(
        recipient_id="recipient-1",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="alicia@example.com",
        phone="+46700000000",
        first_name="Alicia",
        last_name="Andersson",
        company="Northwind",
        status="sent",
        sent_at=requested_at,
    )
    session.store_execution_recipient(
        recipient_id="recipient-2",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="bjorn@example.com",
        phone="+46700000001",
        first_name="Bjorn",
        last_name="Berg",
        company="Northwind",
        status="failed",
        failure_reason="SMTP recipient rejected",
        support_ticket_id="ticket-22",
    )

    csv_text, row_count = await export_marketing_campaign_execution_results_csv(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        execution_id="execution-1",
        recipient_filter="failed",
    )
    rows = list(csv.DictReader(StringIO(csv_text)))

    assert row_count == 1
    assert rows[0]["email"] == "bjorn@example.com"
    assert rows[0]["status"] == "failed"
    assert rows[0]["support_ticket_id"] == "ticket-22"


@pytest.mark.asyncio
async def test_failed_execution_follow_up_handoff_returns_per_recipient_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeMarketingExecutionSession()
    requested_at = datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc)
    session.store_execution(
        execution_id="execution-1",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="failed",
        requested_at=requested_at,
        total_recipients=3,
        processed_recipients=3,
        sent_recipients=1,
        failed_recipients=2,
    )
    session.store_execution_recipient(
        recipient_id="recipient-failed-1",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="bjorn@example.com",
        phone="+46700000001",
        first_name="Bjorn",
        last_name="Berg",
        company="Northwind",
        status="failed",
        failure_reason="SMTP recipient rejected",
    )
    session.store_execution_recipient(
        recipient_id="recipient-failed-2",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="celine@example.com",
        phone="+46700000002",
        first_name="Celine",
        last_name="Carlsson",
        company="Northwind",
        status="failed",
        failure_reason="Mailbox unavailable",
    )
    session.store_execution_recipient(
        recipient_id="recipient-sent",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="alicia@example.com",
        phone="+46700000000",
        first_name="Alicia",
        last_name="Andersson",
        company="Northwind",
        status="sent",
        sent_at=requested_at,
    )

    created_tickets: list[dict[str, str | None]] = []

    async def _fake_create_ticket(*_: object, **kwargs: object):
        recipient_email = str(kwargs["description"]).split("Email: ", 1)[1].split("\n", 1)[0]
        if recipient_email == "celine@example.com":
            raise ValueError("Contact does not exist: contact-missing")
        created_tickets.append(
            {
                "title": str(kwargs["title"]),
                "description": str(kwargs["description"]),
                "contact_id": str(kwargs["contact_id"]) if kwargs.get("contact_id") else None,
            }
        )
        return type("Ticket", (), {"id": "ticket-1"})()

    monkeypatch.setattr(marketing_service, "create_ticket", _fake_create_ticket)

    response = await create_failed_execution_recipient_follow_up_handoff(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        execution_id="execution-1",
        recipient_ids=["recipient-failed-1", "recipient-failed-2", "recipient-sent", "recipient-missing"],
        priority="high",
        handoff_by_user_id="user-1",
    )

    assert response.requested_count == 4
    assert response.created_count == 1
    assert response.failed_count == 3
    assert created_tickets[0]["title"] == "Marketing follow-up: Spring launch failed recipient Bjorn Berg"
    assert "Execution ID: execution-1" in str(created_tickets[0]["description"])
    assert "Failure reason: SMTP recipient rejected" in str(created_tickets[0]["description"])
    assert session.execution_recipients["recipient-failed-1"]["support_ticket_id"] == "ticket-1"
    assert session.execution_recipients["recipient-failed-1"]["handoff_status"] == "created"
    assert session.execution_recipients["recipient-failed-1"]["handoff_by_user_id"] == "user-1"
    assert session.execution_recipients["recipient-failed-1"]["handoff_at"] is not None
    assert session.execution_recipients["recipient-failed-2"]["support_ticket_id"] is None
    assert session.execution_recipients["recipient-failed-2"]["handoff_status"] == "failed"
    assert session.execution_recipients["recipient-failed-2"]["handoff_by_user_id"] == "user-1"
    assert session.execution_recipients["recipient-failed-2"]["handoff_at"] is not None
    assert [(item.recipient_id, item.status, item.support_ticket_id, item.message) for item in response.results] == [
        ("recipient-failed-1", "created", "ticket-1", None),
        ("recipient-failed-2", "failed", None, "Contact does not exist: contact-missing"),
        ("recipient-sent", "failed", None, "Only failed recipients can be handed off for follow-up."),
        ("recipient-missing", "failed", None, "Recipient does not exist in this execution scope."),
    ]


@pytest.mark.asyncio
async def test_failed_execution_follow_up_handoff_prevents_duplicate_ticket_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeMarketingExecutionSession()
    requested_at = datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc)
    session.store_execution(
        execution_id="execution-1",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="failed",
        requested_at=requested_at,
        total_recipients=1,
        processed_recipients=1,
        failed_recipients=1,
    )
    session.store_execution_recipient(
        recipient_id="recipient-failed-1",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="bjorn@example.com",
        phone="+46700000001",
        first_name="Bjorn",
        last_name="Berg",
        company="Northwind",
        status="failed",
        failure_reason="SMTP recipient rejected",
        support_ticket_id="ticket-existing",
        handoff_at=requested_at,
        handoff_by_user_id="user-1",
        handoff_status="created",
    )

    async def _unexpected_create_ticket(*_: object, **__: object):
        raise AssertionError("create_ticket should not run for already handed-off recipients")

    monkeypatch.setattr(marketing_service, "create_ticket", _unexpected_create_ticket)

    response = await create_failed_execution_recipient_follow_up_handoff(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        execution_id="execution-1",
        recipient_ids=["recipient-failed-1"],
        priority="high",
        handoff_by_user_id="user-2",
    )

    assert response.requested_count == 1
    assert response.created_count == 0
    assert response.failed_count == 1
    assert [(item.recipient_id, item.status, item.support_ticket_id, item.message) for item in response.results] == [
        ("recipient-failed-1", "failed", "ticket-existing", "already_handed_off"),
    ]
    assert session.execution_recipients["recipient-failed-1"]["support_ticket_id"] == "ticket-existing"
    assert session.execution_recipients["recipient-failed-1"]["handoff_by_user_id"] == "user-1"
    assert session.execution_recipients["recipient-failed-1"]["handoff_status"] == "created"


@pytest.mark.asyncio
async def test_failed_execution_follow_up_handoff_enforces_execution_scope() -> None:
    session = FakeMarketingExecutionSession()
    session.store_execution(
        execution_id="execution-foreign",
        tenant_id="tenant-2",
        campaign_id="campaign-1",
        status="failed",
        requested_at=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="Campaign execution does not exist"):
        await create_failed_execution_recipient_follow_up_handoff(
            session,
            tenant_id="tenant-1",
            campaign_id="campaign-1",
            execution_id="execution-foreign",
            recipient_ids=["recipient-1"],
            priority="high",
        )


@pytest.mark.asyncio
async def test_execution_readback_includes_handoff_traceability_fields() -> None:
    session = FakeMarketingExecutionSession()
    requested_at = datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc)
    handoff_at = datetime(2026, 4, 21, 9, 30, tzinfo=timezone.utc)
    session.store_execution(
        execution_id="execution-1",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="failed",
        requested_at=requested_at,
        total_recipients=2,
        processed_recipients=2,
        sent_recipients=1,
        failed_recipients=1,
    )
    session.store_execution_recipient(
        recipient_id="recipient-1",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="bjorn@example.com",
        phone="+46700000001",
        first_name="Bjorn",
        last_name="Berg",
        company="Northwind",
        status="failed",
        failure_reason="SMTP recipient rejected",
        support_ticket_id="ticket-123",
        handoff_at=handoff_at,
        handoff_by_user_id="user-7",
        handoff_status="created",
    )
    session.store_execution_recipient(
        recipient_id="recipient-2",
        execution_id="execution-1",
        campaign_id="campaign-1",
        tenant_id="tenant-1",
        email="alicia@example.com",
        phone="+46700000000",
        first_name="Alicia",
        last_name="Andersson",
        company="Northwind",
        status="sent",
        sent_at=requested_at,
    )

    readback = await get_marketing_campaign_execution_readback(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        execution_id="execution-1",
        recipient_filter="failed",
    )

    assert readback.recipient_filter == "failed"
    assert len(readback.recipients) == 1
    assert readback.recipients[0].support_ticket_id == "ticket-123"
    assert readback.recipients[0].handoff_at == handoff_at
    assert readback.recipients[0].handoff_by_user_id == "user-7"
    assert readback.recipients[0].handoff_status == "created"


@pytest.mark.asyncio
async def test_list_marketing_campaign_executions_returns_recent_history() -> None:
    session = FakeMarketingExecutionSession()
    session.store_execution(
        execution_id="execution-1",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="completed",
        requested_at=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )
    session.store_execution(
        execution_id="execution-2",
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        status="failed",
        requested_at=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
    )

    executions = await list_marketing_campaign_executions(
        session,
        tenant_id="tenant-1",
        campaign_id="campaign-1",
        limit=10,
    )

    assert [execution.id for execution in executions] == ["execution-2", "execution-1"]

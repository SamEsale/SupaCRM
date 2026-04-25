from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.security.deps import get_current_principal
from app.db_deps import get_auth_db
from app.main import create_app
from app.marketing import routes as marketing_routes
from app.marketing.service import (
    MarketingExecutionFollowUpHandoffResponse,
    MarketingExecutionFollowUpHandoffResult,
    MarketingAudiencePreviewExclusionCount,
    MarketingAudiencePreviewRecipient,
    MarketingAudienceSummary,
    MarketingCampaignAudiencePreview,
    MarketingCampaignDetail,
    MarketingCampaignDetails,
    MarketingCampaignExecutionDetails,
    MarketingCampaignExecutionReadback,
    MarketingCampaignExecutionRecipientDetails,
    MarketingCampaignExecutionRecipientStatusCount,
    MarketingCampaignExecutionSnapshot,
    MarketingSendReadiness,
)


class _FakeResult:
    def __init__(self, *, scalar: Any = None) -> None:
        self._scalar = scalar

    def scalar_one(self) -> Any:
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakeMarketingRouteSession:
    tenant_id: str = "tenant-alpha"
    user_id: str = "user-alpha"

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()

        if "select exists (" in sql and "from public.tenant_user_roles tur" in sql:
            return _FakeResult(scalar=True)

        raise AssertionError(f"Unhandled SQL in fake marketing route session: {sql}")


@pytest.fixture
def fake_db() -> FakeMarketingRouteSession:
    return FakeMarketingRouteSession()


@pytest_asyncio.fixture
async def client(fake_db: FakeMarketingRouteSession):
    app = create_app()

    async def _override_principal() -> dict[str, Any]:
        return {
            "sub": fake_db.user_id,
            "tenant_id": fake_db.tenant_id,
            "tenant_status": "active",
        }

    async def _override_auth_db():
        yield fake_db

    app.dependency_overrides[get_current_principal] = _override_principal
    app.dependency_overrides[get_auth_db] = _override_auth_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()


def _auth_headers(tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer integration-test-token",
        "X-Tenant-Id": tenant_id,
    }


@pytest.mark.asyncio
async def test_whatsapp_intake_route_surfaces_integrity_failures_as_client_errors(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _raise_integrity_error(*_: object, **__: object):
        raise IntegrityError(
            "insert into public.deals (...)",
            {},
            Exception('new row for relation "deals" violates check constraint "ck_deals_stage_valid"'),
        )

    monkeypatch.setattr(marketing_routes, "create_whatsapp_lead_intake", _raise_integrity_error)

    response = await client.post(
        "/marketing/whatsapp-intake",
        headers=_auth_headers(fake_db.tenant_id),
        json={
            "sender_name": "Alicia Andersson",
            "sender_phone": "+46700000000",
            "message_text": "Can you send pricing?",
            "company_name": "Northwind",
            "amount": "0",
            "currency": "USD",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "bad_request",
            "message": "The WhatsApp intake could not be saved because linked CRM or sales data failed validation.",
        }
    }


@pytest.mark.asyncio
async def test_campaign_audience_preview_route_returns_counts_and_recipients(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)

    async def _fake_preview(*_: object, **__: object) -> MarketingCampaignAudiencePreview:
        return MarketingCampaignAudiencePreview(
            campaign=MarketingCampaignDetails(
                id="campaign-1",
                tenant_id=fake_db.tenant_id,
                name="Spring launch",
                channel="email",
                audience_type="all_contacts",
                audience_description="Qualified contacts",
                target_company_id=None,
                target_contact_id=None,
                subject="Hello",
                message_body="Body",
                status="draft",
                scheduled_for=None,
                blocked_reason=None,
                created_at=now,
                updated_at=now,
            ),
            audience_summary=MarketingAudienceSummary(
                audience_type="all_contacts",
                summary_label="All contacts in the current tenant",
                target_company_label=None,
                target_contact_label=None,
                total_contacts=3,
                email_eligible_contacts=1,
                blocked_reasons=[],
            ),
            send_readiness=MarketingSendReadiness(
                channel="email",
                can_send=True,
                smtp_ready=True,
                queue_ready=True,
                blocked_reasons=[],
                capacity_note="Launch scope only.",
            ),
            total_matched_records=3,
            eligible_recipients=1,
            excluded_recipients=2,
            exclusion_counts=[
                MarketingAudiencePreviewExclusionCount(reason="missing_email", count=1),
                MarketingAudiencePreviewExclusionCount(reason="duplicate_contact_method", count=1),
            ],
            sample_limit=25,
            has_more_recipients=False,
            recipients=[
                MarketingAudiencePreviewRecipient(
                    contact_id="contact-1",
                    contact_name="Alicia Andersson",
                    email="alicia@example.com",
                    phone="+46700000000",
                    company="Northwind",
                    eligibility_status="eligible",
                    exclusion_reason=None,
                ),
                MarketingAudiencePreviewRecipient(
                    contact_id="contact-2",
                    contact_name="Bjorn Berg",
                    email="alicia@example.com",
                    phone="+46700000001",
                    company="Northwind",
                    eligibility_status="duplicate_contact_method",
                    exclusion_reason="Duplicate contact method in this campaign preview.",
                ),
            ],
        )

    monkeypatch.setattr(marketing_routes, "get_marketing_campaign_audience_preview", _fake_preview)

    response = await client.get(
        "/marketing/campaigns/campaign-1/audience-preview",
        headers=_auth_headers(fake_db.tenant_id),
    )

    assert response.status_code == 200
    assert response.json()["eligible_recipients"] == 1
    assert response.json()["excluded_recipients"] == 2
    assert response.json()["exclusion_counts"] == [
        {"reason": "missing_email", "count": 1},
        {"reason": "duplicate_contact_method", "count": 1},
    ]
    assert response.json()["recipients"][1]["exclusion_reason"] == "Duplicate contact method in this campaign preview."


@pytest.mark.asyncio
async def test_campaign_audience_preview_export_route_returns_csv_download(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_export(*_: object, **__: object) -> tuple[str, int]:
        return (
            "contact_name,email,phone,company,eligibility_status,exclusion_reason\r\n"
            "Alicia Andersson,alicia@example.com,+46700000000,Northwind,eligible,\r\n",
            1,
        )

    monkeypatch.setattr(marketing_routes, "export_marketing_campaign_audience_preview_csv", _fake_export)

    response = await client.get(
        "/marketing/campaigns/campaign-1/audience-preview/export",
        headers=_auth_headers(fake_db.tenant_id),
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="campaign-audience-preview.csv"'
    assert response.headers["x-supacrm-row-count"] == "1"
    assert "contact_name,email,phone,company,eligibility_status,exclusion_reason" in response.text


@pytest.mark.asyncio
async def test_campaign_detail_route_returns_latest_execution_snapshot(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)

    async def _fake_detail(*_: object, **__: object) -> MarketingCampaignDetail:
        return MarketingCampaignDetail(
            campaign=MarketingCampaignDetails(
                id="campaign-1",
                tenant_id=fake_db.tenant_id,
                name="Spring launch",
                channel="email",
                audience_type="all_contacts",
                audience_description="Qualified contacts",
                target_company_id=None,
                target_contact_id=None,
                subject="Hello",
                message_body="Body",
                status="sending",
                scheduled_for=None,
                blocked_reason=None,
                created_at=now,
                updated_at=now,
            ),
            audience_summary=MarketingAudienceSummary(
                audience_type="all_contacts",
                summary_label="All contacts in the current tenant",
                target_company_label=None,
                target_contact_label=None,
                total_contacts=3,
                email_eligible_contacts=1,
                blocked_reasons=[],
            ),
            send_readiness=MarketingSendReadiness(
                channel="email",
                can_send=True,
                smtp_ready=True,
                queue_ready=True,
                blocked_reasons=[],
                capacity_note="Launch scope only.",
            ),
            latest_execution=MarketingCampaignExecutionDetails(
                id="execution-1",
                tenant_id=fake_db.tenant_id,
                campaign_id="campaign-1",
                channel="email",
                status="sending",
                total_recipients=1,
                processed_recipients=0,
                sent_recipients=0,
                failed_recipients=0,
                batch_size=100,
                queued_batch_count=1,
                queue_job_id="job-1",
                blocked_reason=None,
                requested_at=now,
                started_at=now,
                completed_at=None,
                created_at=now,
                updated_at=now,
                snapshot=MarketingCampaignExecutionSnapshot(
                    audience_type="all_contacts",
                    summary_label="All contacts in the current tenant",
                    target_company_label=None,
                    target_contact_label=None,
                    total_matched_records=3,
                    eligible_recipients=1,
                    excluded_recipients=2,
                    exclusion_counts=[
                        MarketingAudiencePreviewExclusionCount(reason="missing_email", count=1),
                        MarketingAudiencePreviewExclusionCount(reason="duplicate_contact_method", count=1),
                    ],
                ),
            ),
            latest_execution_snapshot=MarketingCampaignExecutionSnapshot(
                audience_type="all_contacts",
                summary_label="All contacts in the current tenant",
                target_company_label=None,
                target_contact_label=None,
                total_matched_records=3,
                eligible_recipients=1,
                excluded_recipients=2,
                exclusion_counts=[
                    MarketingAudiencePreviewExclusionCount(reason="missing_email", count=1),
                    MarketingAudiencePreviewExclusionCount(reason="duplicate_contact_method", count=1),
                ],
            ),
            recent_recipients=[
                MarketingCampaignExecutionRecipientDetails(
                    id="recipient-1",
                    execution_id="execution-1",
                    campaign_id="campaign-1",
                    contact_id="contact-1",
                    contact_name="Alicia Andersson",
                    email="alicia@example.com",
                    phone="+46700000000",
                    first_name="Alicia",
                    last_name="Andersson",
                    company="Northwind",
                    batch_number=1,
                    status="pending",
                    failure_reason=None,
                    support_ticket_id=None,
                    handoff_at=None,
                    handoff_by_user_id=None,
                    handoff_status=None,
                    sent_at=None,
                )
            ],
            execution_history=[
                MarketingCampaignExecutionDetails(
                    id="execution-1",
                    tenant_id=fake_db.tenant_id,
                    campaign_id="campaign-1",
                    channel="email",
                    status="sending",
                    total_recipients=1,
                    processed_recipients=0,
                    sent_recipients=0,
                    failed_recipients=0,
                    batch_size=100,
                    queued_batch_count=1,
                    queue_job_id="job-1",
                    blocked_reason=None,
                    requested_at=now,
                    started_at=now,
                    completed_at=None,
                    created_at=now,
                    updated_at=now,
                    snapshot=None,
                )
            ],
        )

    monkeypatch.setattr(marketing_routes, "get_marketing_campaign_detail", _fake_detail)

    response = await client.get(
        "/marketing/campaigns/campaign-1",
        headers=_auth_headers(fake_db.tenant_id),
    )

    assert response.status_code == 200
    assert response.json()["latest_execution"]["status"] == "sending"
    assert response.json()["latest_execution_snapshot"]["eligible_recipients"] == 1
    assert response.json()["execution_history"][0]["id"] == "execution-1"
    assert response.json()["recent_recipients"][0]["email"] == "alicia@example.com"
    assert response.json()["recent_recipients"][0]["phone"] == "+46700000000"


@pytest.mark.asyncio
async def test_campaign_send_email_route_returns_latest_execution_detail(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)

    async def _fake_start(*_: object, **__: object) -> MarketingCampaignDetail:
        return MarketingCampaignDetail(
            campaign=MarketingCampaignDetails(
                id="campaign-1",
                tenant_id=fake_db.tenant_id,
                name="Spring launch",
                channel="email",
                audience_type="all_contacts",
                audience_description="Qualified contacts",
                target_company_id=None,
                target_contact_id=None,
                subject="Hello",
                message_body="Body",
                status="sending",
                scheduled_for=None,
                blocked_reason=None,
                created_at=now,
                updated_at=now,
            ),
            audience_summary=MarketingAudienceSummary(
                audience_type="all_contacts",
                summary_label="All contacts in the current tenant",
                target_company_label=None,
                target_contact_label=None,
                total_contacts=3,
                email_eligible_contacts=1,
                blocked_reasons=[],
            ),
            send_readiness=MarketingSendReadiness(
                channel="email",
                can_send=True,
                smtp_ready=True,
                queue_ready=True,
                blocked_reasons=[],
                capacity_note="Launch scope only.",
            ),
            latest_execution=MarketingCampaignExecutionDetails(
                id="execution-1",
                tenant_id=fake_db.tenant_id,
                campaign_id="campaign-1",
                channel="email",
                status="sending",
                total_recipients=1,
                processed_recipients=0,
                sent_recipients=0,
                failed_recipients=0,
                batch_size=100,
                queued_batch_count=1,
                queue_job_id="job-1",
                blocked_reason=None,
                requested_at=now,
                started_at=now,
                completed_at=None,
                created_at=now,
                updated_at=now,
                snapshot=MarketingCampaignExecutionSnapshot(
                    audience_type="all_contacts",
                    summary_label="All contacts in the current tenant",
                    target_company_label=None,
                    target_contact_label=None,
                    total_matched_records=3,
                    eligible_recipients=1,
                    excluded_recipients=2,
                    exclusion_counts=[
                        MarketingAudiencePreviewExclusionCount(reason="missing_email", count=1),
                    ],
                ),
            ),
            latest_execution_snapshot=MarketingCampaignExecutionSnapshot(
                audience_type="all_contacts",
                summary_label="All contacts in the current tenant",
                target_company_label=None,
                target_contact_label=None,
                total_matched_records=3,
                eligible_recipients=1,
                excluded_recipients=2,
                exclusion_counts=[
                    MarketingAudiencePreviewExclusionCount(reason="missing_email", count=1),
                ],
            ),
            recent_recipients=[],
            execution_history=[
                MarketingCampaignExecutionDetails(
                    id="execution-1",
                    tenant_id=fake_db.tenant_id,
                    campaign_id="campaign-1",
                    channel="email",
                    status="sending",
                    total_recipients=1,
                    processed_recipients=0,
                    sent_recipients=0,
                    failed_recipients=0,
                    batch_size=100,
                    queued_batch_count=1,
                    queue_job_id="job-1",
                    blocked_reason=None,
                    requested_at=now,
                    started_at=now,
                    completed_at=None,
                    created_at=now,
                    updated_at=now,
                    snapshot=None,
                )
            ],
        )

    monkeypatch.setattr(marketing_routes, "start_email_campaign_execution", _fake_start)

    response = await client.post(
        "/marketing/campaigns/campaign-1/send-email",
        headers=_auth_headers(fake_db.tenant_id),
    )

    assert response.status_code == 200
    assert response.json()["campaign"]["status"] == "sending"
    assert response.json()["latest_execution"]["queue_job_id"] == "job-1"
    assert response.json()["latest_execution_snapshot"]["total_matched_records"] == 3
    assert response.json()["execution_history"][0]["id"] == "execution-1"


@pytest.mark.asyncio
async def test_campaign_execution_history_route_returns_recent_executions(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)

    async def _fake_history(*_: object, **__: object) -> list[MarketingCampaignExecutionDetails]:
        return [
            MarketingCampaignExecutionDetails(
                id="execution-2",
                tenant_id=fake_db.tenant_id,
                campaign_id="campaign-1",
                channel="email",
                status="failed",
                total_recipients=2,
                processed_recipients=2,
                sent_recipients=1,
                failed_recipients=1,
                batch_size=100,
                queued_batch_count=1,
                queue_job_id="job-2",
                blocked_reason="One recipient failed.",
                requested_at=now,
                started_at=now,
                completed_at=now,
                created_at=now,
                updated_at=now,
                snapshot=None,
            ),
            MarketingCampaignExecutionDetails(
                id="execution-1",
                tenant_id=fake_db.tenant_id,
                campaign_id="campaign-1",
                channel="email",
                status="completed",
                total_recipients=1,
                processed_recipients=1,
                sent_recipients=1,
                failed_recipients=0,
                batch_size=100,
                queued_batch_count=1,
                queue_job_id="job-1",
                blocked_reason=None,
                requested_at=now,
                started_at=now,
                completed_at=now,
                created_at=now,
                updated_at=now,
                snapshot=None,
            ),
        ]

    monkeypatch.setattr(marketing_routes, "list_marketing_campaign_executions", _fake_history)

    response = await client.get(
        "/marketing/campaigns/campaign-1/executions",
        headers=_auth_headers(fake_db.tenant_id),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["execution-2", "execution-1"]


@pytest.mark.asyncio
async def test_campaign_execution_readback_route_returns_filtered_recipients(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)

    async def _fake_readback(*_: object, **__: object) -> MarketingCampaignExecutionReadback:
        return MarketingCampaignExecutionReadback(
            execution=MarketingCampaignExecutionDetails(
                id="execution-2",
                tenant_id=fake_db.tenant_id,
                campaign_id="campaign-1",
                channel="email",
                status="failed",
                total_recipients=2,
                processed_recipients=2,
                sent_recipients=1,
                failed_recipients=1,
                batch_size=100,
                queued_batch_count=1,
                queue_job_id="job-2",
                blocked_reason="One recipient failed.",
                requested_at=now,
                started_at=now,
                completed_at=now,
                created_at=now,
                updated_at=now,
                snapshot=MarketingCampaignExecutionSnapshot(
                    audience_type="all_contacts",
                    summary_label="All contacts in the current tenant",
                    target_company_label=None,
                    target_contact_label=None,
                    total_matched_records=2,
                    eligible_recipients=2,
                    excluded_recipients=0,
                    exclusion_counts=[],
                ),
            ),
            execution_snapshot=MarketingCampaignExecutionSnapshot(
                audience_type="all_contacts",
                summary_label="All contacts in the current tenant",
                target_company_label=None,
                target_contact_label=None,
                total_matched_records=2,
                eligible_recipients=2,
                excluded_recipients=0,
                exclusion_counts=[],
            ),
            recipient_filter="failed",
            recipient_counts=[
                MarketingCampaignExecutionRecipientStatusCount(status="all", count=2),
                MarketingCampaignExecutionRecipientStatusCount(status="failed", count=1),
                MarketingCampaignExecutionRecipientStatusCount(status="sent", count=1),
                MarketingCampaignExecutionRecipientStatusCount(status="pending", count=0),
                MarketingCampaignExecutionRecipientStatusCount(status="blocked", count=0),
            ],
            recipients=[
                MarketingCampaignExecutionRecipientDetails(
                    id="recipient-2",
                    execution_id="execution-2",
                    campaign_id="campaign-1",
                    contact_id="contact-2",
                    contact_name="Bjorn Berg",
                    email="bjorn@example.com",
                    phone="+46700000001",
                    first_name="Bjorn",
                    last_name="Berg",
                    company="Northwind",
                    batch_number=1,
                    status="failed",
                    failure_reason="SMTP recipient rejected",
                    support_ticket_id="ticket-1",
                    handoff_at=now,
                    handoff_by_user_id=fake_db.user_id,
                    handoff_status="created",
                    sent_at=None,
                )
            ],
        )

    monkeypatch.setattr(marketing_routes, "get_marketing_campaign_execution_readback", _fake_readback)

    response = await client.get(
        "/marketing/campaigns/campaign-1/executions/execution-2",
        headers=_auth_headers(fake_db.tenant_id),
        params={"recipient_status": "failed"},
    )

    assert response.status_code == 200
    assert response.json()["recipient_filter"] == "failed"
    assert response.json()["recipient_counts"][1] == {"status": "failed", "count": 1}
    assert response.json()["recipients"][0]["contact_name"] == "Bjorn Berg"
    assert response.json()["recipients"][0]["failure_reason"] == "SMTP recipient rejected"
    assert response.json()["recipients"][0]["support_ticket_id"] == "ticket-1"
    assert response.json()["recipients"][0]["handoff_by_user_id"] == fake_db.user_id
    assert response.json()["recipients"][0]["handoff_status"] == "created"


@pytest.mark.asyncio
async def test_campaign_execution_results_export_route_returns_csv_download(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_export(*_: object, **__: object) -> tuple[str, int]:
        return (
            "execution_id,campaign_id,contact_name,email,phone,company,status,failure_reason,support_ticket_id,sent_at,batch_number\r\n"
            "execution-2,campaign-1,Bjorn Berg,bjorn@example.com,+46700000001,Northwind,failed,SMTP recipient rejected,ticket-1,,1\r\n",
            1,
        )

    monkeypatch.setattr(marketing_routes, "export_marketing_campaign_execution_results_csv", _fake_export)

    response = await client.get(
        "/marketing/campaigns/campaign-1/executions/execution-2/export",
        headers=_auth_headers(fake_db.tenant_id),
        params={"recipient_status": "failed"},
    )

    assert response.status_code == 200
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="campaign-execution-results-execution-2.csv"'
    )
    assert response.headers["x-supacrm-row-count"] == "1"
    assert "support_ticket_id" in response.text
    assert "ticket-1" in response.text


@pytest.mark.asyncio
async def test_campaign_execution_follow_up_handoff_route_returns_result_counts(
    client: AsyncClient,
    fake_db: FakeMarketingRouteSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logged_events: list[dict[str, Any]] = []

    async def _fake_handoff(*_: object, **__: object) -> MarketingExecutionFollowUpHandoffResponse:
        return MarketingExecutionFollowUpHandoffResponse(
            execution_id="execution-2",
            campaign_id="campaign-1",
            requested_count=2,
            created_count=1,
            failed_count=1,
            results=[
                MarketingExecutionFollowUpHandoffResult(
                    recipient_id="recipient-1",
                    contact_name="Bjorn Berg",
                    email="bjorn@example.com",
                    status="created",
                    support_ticket_id="ticket-1",
                    message=None,
                ),
                MarketingExecutionFollowUpHandoffResult(
                    recipient_id="recipient-2",
                    contact_name="Dana Dahl",
                    email="dana@example.com",
                    status="failed",
                    support_ticket_id=None,
                    message="Recipient does not exist in this execution scope.",
                ),
            ],
        )

    async def _fake_audit_log(**kwargs: Any) -> None:
        logged_events.append(kwargs)

    monkeypatch.setattr(marketing_routes, "create_failed_execution_recipient_follow_up_handoff", _fake_handoff)
    monkeypatch.setattr(marketing_routes.AuditService, "log", _fake_audit_log)

    response = await client.post(
        "/marketing/campaigns/campaign-1/executions/execution-2/follow-up-handoff",
        headers=_auth_headers(fake_db.tenant_id),
        json={
            "recipient_ids": ["recipient-1", "recipient-2"],
            "priority": "high",
        },
    )

    assert response.status_code == 200
    assert response.json()["created_count"] == 1
    assert response.json()["failed_count"] == 1
    assert response.json()["results"][0]["support_ticket_id"] == "ticket-1"
    assert response.json()["results"][1]["message"] == "Recipient does not exist in this execution scope."
    assert logged_events == [
        {
            "db": fake_db,
            "tenant_id": fake_db.tenant_id,
            "action": "MARKETING_EXECUTION_HANDOFF_CREATED",
            "actor_user_id": fake_db.user_id,
            "resource": "marketing_execution",
            "resource_id": "execution-2",
            "status_code": 200,
            "message": "Marketing execution failed recipients handed off into support tickets.",
            "meta": {
                "campaign_id": "campaign-1",
                "execution_id": "execution-2",
                "recipient_ids": ["recipient-1"],
                "ticket_ids": ["ticket-1"],
            },
        }
    ]

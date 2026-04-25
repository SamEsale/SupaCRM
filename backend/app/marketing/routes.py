from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.core.security.deps import get_current_principal, get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.marketing.schemas import (
    MarketingAudienceSummaryOut,
    MarketingCampaignCreateRequest,
    MarketingCampaignAudiencePreviewOut,
    MarketingCampaignDetailOut,
    MarketingCampaignExecutionDetailOut,
    MarketingCampaignExecutionListResponse,
    MarketingCampaignExecutionOut,
    MarketingCampaignExecutionRecipientOut,
    MarketingCampaignExecutionRecipientStatusCountOut,
    MarketingCampaignExecutionSnapshotOut,
    MarketingExecutionFollowUpHandoffRequest,
    MarketingExecutionFollowUpHandoffResponseOut,
    MarketingExecutionFollowUpHandoffResultStatusOut,
    MarketingAudiencePreviewExclusionCountOut,
    MarketingAudiencePreviewRecipientOut,
    MarketingCampaignListResponse,
    MarketingCampaignOut,
    MarketingCampaignUpdateRequest,
    MarketingIntegrationsOut,
    MarketingRecordReferenceOut,
    MarketingSendReadinessOut,
    SmtpConnectionTestResponse,
    SmtpSettingsOut,
    SmtpSettingsUpdateRequest,
    WhatsAppLeadIntakeOut,
    WhatsAppLeadIntakeRequest,
    WhatsAppIntegrationSettingsOut,
    WhatsAppIntegrationSettingsUpdateRequest,
)
from app.marketing.service import (
    create_marketing_campaign,
    create_whatsapp_lead_intake,
    create_failed_execution_recipient_follow_up_handoff,
    export_marketing_campaign_audience_preview_csv,
    export_marketing_campaign_execution_results_csv,
    get_marketing_campaign_audience_preview,
    get_marketing_campaign_detail,
    get_marketing_campaign_execution_readback,
    get_marketing_integrations,
    list_marketing_campaign_executions,
    list_marketing_campaigns,
    start_email_campaign_execution,
    test_smtp_connection,
    update_marketing_campaign,
    update_smtp_settings,
    update_whatsapp_settings,
)
from app.rbac.permissions import (
    PERMISSION_CRM_WRITE,
    PERMISSION_SALES_READ,
    PERMISSION_SALES_WRITE,
    PERMISSION_SUPPORT_WRITE,
    PERMISSION_TENANT_ADMIN,
)

router = APIRouter(prefix="/marketing", tags=["marketing"])


def _execution_out(execution) -> MarketingCampaignExecutionOut:
    return MarketingCampaignExecutionOut(
        id=execution.id,
        tenant_id=execution.tenant_id,
        campaign_id=execution.campaign_id,
        channel=execution.channel,
        status=execution.status,
        total_recipients=execution.total_recipients,
        processed_recipients=execution.processed_recipients,
        sent_recipients=execution.sent_recipients,
        failed_recipients=execution.failed_recipients,
        batch_size=execution.batch_size,
        queued_batch_count=execution.queued_batch_count,
        queue_job_id=execution.queue_job_id,
        blocked_reason=execution.blocked_reason,
        requested_at=execution.requested_at,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        created_at=execution.created_at,
        updated_at=execution.updated_at,
    )


def _execution_snapshot_out(snapshot) -> MarketingCampaignExecutionSnapshotOut:
    return MarketingCampaignExecutionSnapshotOut(
        audience_type=snapshot.audience_type,
        summary_label=snapshot.summary_label,
        target_company_label=snapshot.target_company_label,
        target_contact_label=snapshot.target_contact_label,
        total_matched_records=snapshot.total_matched_records,
        eligible_recipients=snapshot.eligible_recipients,
        excluded_recipients=snapshot.excluded_recipients,
        exclusion_counts=[
            MarketingAudiencePreviewExclusionCountOut(**asdict(item))
            for item in snapshot.exclusion_counts
        ],
    )


def _execution_recipient_out(recipient) -> MarketingCampaignExecutionRecipientOut:
    return MarketingCampaignExecutionRecipientOut(
        id=recipient.id,
        execution_id=recipient.execution_id,
        campaign_id=recipient.campaign_id,
        contact_id=recipient.contact_id,
        contact_name=recipient.contact_name,
        email=recipient.email,
        phone=recipient.phone,
        first_name=recipient.first_name,
        last_name=recipient.last_name,
        company=recipient.company,
        batch_number=recipient.batch_number,
        status=recipient.status,
        failure_reason=recipient.failure_reason,
        support_ticket_id=recipient.support_ticket_id,
        handoff_at=recipient.handoff_at,
        handoff_by_user_id=recipient.handoff_by_user_id,
        handoff_status=recipient.handoff_status,
        sent_at=recipient.sent_at,
    )


def _campaign_detail_out(detail) -> MarketingCampaignDetailOut:
    latest_execution = _execution_out(detail.latest_execution) if detail.latest_execution else None
    latest_execution_snapshot = (
        _execution_snapshot_out(detail.latest_execution_snapshot)
        if detail.latest_execution_snapshot
        else None
    )

    return MarketingCampaignDetailOut(
        campaign=MarketingCampaignOut(**asdict(detail.campaign)),
        audience_summary=MarketingAudienceSummaryOut(**asdict(detail.audience_summary)),
        send_readiness=MarketingSendReadinessOut(**asdict(detail.send_readiness)),
        latest_execution=latest_execution,
        latest_execution_snapshot=latest_execution_snapshot,
        execution_history=[_execution_out(item) for item in detail.execution_history],
        recent_recipients=[_execution_recipient_out(item) for item in detail.recent_recipients],
    )


def _execution_readback_out(readback) -> MarketingCampaignExecutionDetailOut:
    return MarketingCampaignExecutionDetailOut(
        execution=_execution_out(readback.execution),
        execution_snapshot=(
            _execution_snapshot_out(readback.execution_snapshot)
            if readback.execution_snapshot
            else None
        ),
        recipient_filter=readback.recipient_filter,
        recipient_counts=[
            MarketingCampaignExecutionRecipientStatusCountOut(**asdict(item))
            for item in readback.recipient_counts
        ],
        recipients=[_execution_recipient_out(item) for item in readback.recipients],
    )


def _execution_follow_up_handoff_out(response) -> MarketingExecutionFollowUpHandoffResponseOut:
    return MarketingExecutionFollowUpHandoffResponseOut(
        execution_id=response.execution_id,
        campaign_id=response.campaign_id,
        requested_count=response.requested_count,
        created_count=response.created_count,
        failed_count=response.failed_count,
        results=[
            MarketingExecutionFollowUpHandoffResultStatusOut(**asdict(item))
            for item in response.results
        ],
    )


def _raise_for_marketing_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Campaign does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if detail.startswith("Campaign execution does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if (
        detail.startswith("Company does not exist")
        or detail.startswith("Contact does not exist")
        or detail.startswith("Campaign target")
        or detail.startswith("Invalid campaign")
        or detail.startswith("Scheduled campaigns require")
        or detail.startswith("Email campaigns require")
        or detail.startswith("Select an existing company")
        or detail.startswith("Amount must be")
        or detail.startswith("Currency must be")
        or detail.startswith("Invalid execution recipient filter")
        or detail.startswith("Select at least one failed recipient")
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get(
    "/integrations",
    response_model=MarketingIntegrationsOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def get_marketing_integrations_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingIntegrationsOut:
    integrations = await get_marketing_integrations(db, tenant_id=tenant_id)
    return MarketingIntegrationsOut(
        whatsapp=WhatsAppIntegrationSettingsOut(**asdict(integrations.whatsapp)),
        smtp=SmtpSettingsOut(**asdict(integrations.smtp)),
    )


@router.put(
    "/integrations/whatsapp",
    response_model=WhatsAppIntegrationSettingsOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def update_whatsapp_integration_route(
    payload: WhatsAppIntegrationSettingsUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> WhatsAppIntegrationSettingsOut:
    try:
        integration = await update_whatsapp_settings(
            db,
            tenant_id=tenant_id,
            business_account_id=payload.business_account_id,
            phone_number_id=payload.phone_number_id,
            display_name=payload.display_name,
            access_token=payload.access_token,
            webhook_verify_token=payload.webhook_verify_token,
            is_enabled=payload.is_enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WhatsAppIntegrationSettingsOut(**asdict(integration))


@router.put(
    "/integrations/smtp",
    response_model=SmtpSettingsOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def update_smtp_integration_route(
    payload: SmtpSettingsUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SmtpSettingsOut:
    try:
        integration = await update_smtp_settings(
            db,
            tenant_id=tenant_id,
            smtp_host=payload.smtp_host,
            smtp_port=payload.smtp_port,
            smtp_username=payload.smtp_username,
            smtp_password=payload.smtp_password,
            from_email=str(payload.from_email) if payload.from_email else None,
            from_name=payload.from_name,
            use_tls=payload.use_tls,
            use_ssl=payload.use_ssl,
            is_enabled=payload.is_enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SmtpSettingsOut(**asdict(integration))


@router.post(
    "/integrations/smtp/test",
    response_model=SmtpConnectionTestResponse,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def test_smtp_integration_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SmtpConnectionTestResponse:
    try:
        _, message = await test_smtp_connection(db, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SmtpConnectionTestResponse(success=True, message=message)


@router.get(
    "/campaigns",
    response_model=MarketingCampaignListResponse,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def list_marketing_campaigns_route(
    q: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingCampaignListResponse:
    try:
        result = await list_marketing_campaigns(
            db,
            tenant_id=tenant_id,
            q=q,
            channel=channel,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    return MarketingCampaignListResponse(
        items=[MarketingCampaignOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.post(
    "/campaigns",
    response_model=MarketingCampaignOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def create_marketing_campaign_route(
    payload: MarketingCampaignCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingCampaignOut:
    try:
        campaign = await create_marketing_campaign(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            channel=payload.channel,
            audience_type=payload.audience_type,
            audience_description=payload.audience_description,
            target_company_id=payload.target_company_id,
            target_contact_id=payload.target_contact_id,
            subject=payload.subject,
            message_body=payload.message_body,
            status=payload.status,
            scheduled_for=payload.scheduled_for,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc
    return MarketingCampaignOut(**asdict(campaign))


@router.put(
    "/campaigns/{campaign_id}",
    response_model=MarketingCampaignOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def update_marketing_campaign_route(
    campaign_id: str,
    payload: MarketingCampaignUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingCampaignOut:
    try:
        campaign = await update_marketing_campaign(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            name=payload.name,
            channel=payload.channel,
            audience_type=payload.audience_type,
            audience_description=payload.audience_description,
            target_company_id=payload.target_company_id,
            target_contact_id=payload.target_contact_id,
            subject=payload.subject,
            message_body=payload.message_body,
            status=payload.status,
            scheduled_for=payload.scheduled_for,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc
    return MarketingCampaignOut(**asdict(campaign))


@router.get(
    "/campaigns/{campaign_id}",
    response_model=MarketingCampaignDetailOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def get_marketing_campaign_detail_route(
    campaign_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingCampaignDetailOut:
    try:
        detail = await get_marketing_campaign_detail(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    return _campaign_detail_out(detail)


@router.get(
    "/campaigns/{campaign_id}/executions",
    response_model=MarketingCampaignExecutionListResponse,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def list_marketing_campaign_executions_route(
    campaign_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingCampaignExecutionListResponse:
    try:
        executions = await list_marketing_campaign_executions(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            limit=limit,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    return MarketingCampaignExecutionListResponse(items=[_execution_out(item) for item in executions])


@router.get(
    "/campaigns/{campaign_id}/executions/{execution_id}",
    response_model=MarketingCampaignExecutionDetailOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def get_marketing_campaign_execution_readback_route(
    campaign_id: str,
    execution_id: str,
    recipient_status: str = Query(default="all"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingCampaignExecutionDetailOut:
    try:
        readback = await get_marketing_campaign_execution_readback(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            execution_id=execution_id,
            recipient_filter=recipient_status,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    return _execution_readback_out(readback)


@router.get(
    "/campaigns/{campaign_id}/executions/{execution_id}/export",
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def export_marketing_campaign_execution_results_route(
    campaign_id: str,
    execution_id: str,
    recipient_status: str = Query(default="all"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> Response:
    try:
        csv_text, row_count = await export_marketing_campaign_execution_results_csv(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            execution_id=execution_id,
            recipient_filter=recipient_status,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="campaign-execution-results-{execution_id}.csv"',
            "X-SupaCRM-Row-Count": str(row_count),
        },
    )


@router.post(
    "/campaigns/{campaign_id}/executions/{execution_id}/follow-up-handoff",
    response_model=MarketingExecutionFollowUpHandoffResponseOut,
    dependencies=[Depends(require_permission(PERMISSION_SUPPORT_WRITE))],
)
async def create_failed_execution_follow_up_handoff_route(
    campaign_id: str,
    execution_id: str,
    payload: MarketingExecutionFollowUpHandoffRequest,
    principal: dict = Depends(get_current_principal),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingExecutionFollowUpHandoffResponseOut:
    try:
        response = await create_failed_execution_recipient_follow_up_handoff(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            execution_id=execution_id,
            recipient_ids=payload.recipient_ids,
            priority=payload.priority,
            handoff_by_user_id=str(principal.get("sub")) if principal.get("sub") else None,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    if response.created_count > 0:
        created_recipient_ids = [
            item.recipient_id for item in response.results if item.status == "created"
        ]
        created_ticket_ids = [
            item.support_ticket_id
            for item in response.results
            if item.status == "created" and item.support_ticket_id
        ]
        await AuditService.log(
            db=db,
            tenant_id=tenant_id,
            action="MARKETING_EXECUTION_HANDOFF_CREATED",
            actor_user_id=str(principal.get("sub")) if principal.get("sub") else None,
            resource="marketing_execution",
            resource_id=execution_id,
            status_code=200,
            message="Marketing execution failed recipients handed off into support tickets.",
            meta={
                "campaign_id": campaign_id,
                "execution_id": execution_id,
                "recipient_ids": created_recipient_ids,
                "ticket_ids": created_ticket_ids,
            },
        )

    return _execution_follow_up_handoff_out(response)


@router.post(
    "/campaigns/{campaign_id}/send-email",
    response_model=MarketingCampaignDetailOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def start_marketing_campaign_email_send_route(
    campaign_id: str,
    principal: dict = Depends(get_current_principal),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingCampaignDetailOut:
    try:
        detail = await start_email_campaign_execution(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            initiated_by_user_id=str(principal.get("sub")) if principal.get("sub") else None,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    return _campaign_detail_out(detail)


@router.get(
    "/campaigns/{campaign_id}/audience-preview",
    response_model=MarketingCampaignAudiencePreviewOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def get_marketing_campaign_audience_preview_route(
    campaign_id: str,
    sample_limit: int = Query(default=25, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> MarketingCampaignAudiencePreviewOut:
    try:
        preview = await get_marketing_campaign_audience_preview(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            sample_limit=sample_limit,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    return MarketingCampaignAudiencePreviewOut(
        campaign=MarketingCampaignOut(**asdict(preview.campaign)),
        audience_summary=MarketingAudienceSummaryOut(**asdict(preview.audience_summary)),
        send_readiness=MarketingSendReadinessOut(**asdict(preview.send_readiness)),
        total_matched_records=preview.total_matched_records,
        eligible_recipients=preview.eligible_recipients,
        excluded_recipients=preview.excluded_recipients,
        exclusion_counts=[
            MarketingAudiencePreviewExclusionCountOut(**asdict(item))
            for item in preview.exclusion_counts
        ],
        sample_limit=preview.sample_limit,
        has_more_recipients=preview.has_more_recipients,
        recipients=[
            MarketingAudiencePreviewRecipientOut(**asdict(item))
            for item in preview.recipients
        ],
    )


@router.get(
    "/campaigns/{campaign_id}/audience-preview/export",
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def export_marketing_campaign_audience_preview_route(
    campaign_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> Response:
    try:
        csv_text, row_count = await export_marketing_campaign_audience_preview_csv(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc

    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="campaign-audience-preview.csv"',
            "X-SupaCRM-Row-Count": str(row_count),
        },
    )


@router.post(
    "/whatsapp-intake",
    response_model=WhatsAppLeadIntakeOut,
    dependencies=[
        Depends(require_permission(PERMISSION_CRM_WRITE)),
        Depends(require_permission(PERMISSION_SALES_WRITE)),
    ],
)
async def create_whatsapp_lead_intake_route(
    payload: WhatsAppLeadIntakeRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> WhatsAppLeadIntakeOut:
    try:
        result = await create_whatsapp_lead_intake(
            db,
            tenant_id=tenant_id,
            sender_name=payload.sender_name,
            sender_phone=payload.sender_phone,
            message_text=payload.message_text,
            message_type=payload.message_type,
            received_at=payload.received_at,
            company_id=payload.company_id,
            company_name=payload.company_name,
            contact_id=payload.contact_id,
            email=str(payload.email) if payload.email else None,
            amount=payload.amount,
            currency=payload.currency,
            campaign_id=payload.campaign_id,
            notes=payload.notes,
            whatsapp_account_id=payload.whatsapp_account_id,
        )
    except ValueError as exc:
        raise _raise_for_marketing_service_error(exc) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The WhatsApp intake could not be saved because linked CRM or sales data failed validation.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The WhatsApp intake failed unexpectedly on the backend. Check migrations and retry.",
        ) from exc

    return WhatsAppLeadIntakeOut(
        deal=MarketingRecordReferenceOut(**asdict(result.deal)),
        company=MarketingRecordReferenceOut(**asdict(result.company)),
        contact=MarketingRecordReferenceOut(**asdict(result.contact)) if result.contact else None,
        campaign=MarketingRecordReferenceOut(**asdict(result.campaign)) if result.campaign else None,
    )

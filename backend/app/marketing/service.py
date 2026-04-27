from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from io import StringIO
import json
import math
import uuid
from typing import Any

import aiosmtplib
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crm.service import (
    CompanyDetails,
    ContactDetails,
    create_company,
    create_contact,
    get_company_by_id,
    get_contact_by_id,
)
from app.sales.service import create_deal
from app.sales.whatsapp_integration import (
    build_new_lead_contact_defaults,
    build_new_lead_deal_defaults,
    parse_inbound_whatsapp_lead,
)
from app.support.service import create_ticket
from app.workers.queue import enqueue_marketing_campaign_execution
from app.marketing.social_catalog import (
    SOCIAL_PROVIDER_CAPABILITIES,
    SOCIAL_PROVIDER_DISPLAY_NAMES,
    SOCIAL_PROVIDER_REQUIRED_FIELDS,
    SUPPORTED_SOCIAL_PROVIDERS,
)


ALLOWED_CAMPAIGN_CHANNELS: tuple[str, ...] = ("email", "whatsapp")
ALLOWED_CAMPAIGN_EDITABLE_STATUSES: tuple[str, ...] = ("draft", "scheduled")
ALLOWED_CAMPAIGN_STATUSES: tuple[str, ...] = (
    "draft",
    "scheduled",
    "sending",
    "completed",
    "failed",
    "blocked",
)
ALLOWED_CAMPAIGN_AUDIENCE_TYPES: tuple[str, ...] = (
    "all_contacts",
    "target_company_contacts",
    "target_contact_only",
)
ALLOWED_AUDIENCE_PREVIEW_RECIPIENT_STATUSES: tuple[str, ...] = (
    "eligible",
    "missing_email",
    "missing_phone",
    "excluded_by_target_context",
    "duplicate_contact_method",
    "blocked_by_campaign_rules",
)
ALLOWED_EXECUTION_STATUSES: tuple[str, ...] = ("queued", "sending", "completed", "failed", "blocked")
ALLOWED_EXECUTION_RECIPIENT_STATUSES: tuple[str, ...] = ("pending", "sent", "failed", "blocked")
ALLOWED_EXECUTION_RECIPIENT_FILTERS: tuple[str, ...] = ("all", "failed", "sent", "pending", "blocked")
EMAIL_CAMPAIGN_BATCH_SIZE = 100
MARKETING_AUDIENCE_PREVIEW_DEFAULT_LIMIT = 25
MARKETING_EXECUTION_HISTORY_DEFAULT_LIMIT = 10
EMAIL_CAMPAIGN_CAPACITY_NOTE = (
    "Launch scope uses tenant SMTP with queued batches of up to 100 recipients. "
    "Large-scale daily throughput is not certified yet."
)


@dataclass(slots=True)
class WhatsAppIntegrationDetails:
    business_account_id: str | None
    phone_number_id: str | None
    display_name: str | None
    access_token_set: bool
    webhook_verify_token_set: bool
    is_enabled: bool
    updated_at: datetime | None


@dataclass(slots=True)
class SmtpSettingsDetails:
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    from_email: str | None
    from_name: str | None
    use_tls: bool
    use_ssl: bool
    password_set: bool
    is_enabled: bool
    updated_at: datetime | None


@dataclass(slots=True)
class MarketingIntegrationsDetails:
    whatsapp: WhatsAppIntegrationDetails
    smtp: SmtpSettingsDetails
    social: list["SocialIntegrationProviderDetails"]


@dataclass(slots=True)
class SocialIntegrationProviderDetails:
    provider: str
    display_name: str
    account_id: str | None
    account_name: str | None
    page_id: str | None
    profile_id: str | None
    access_token_set: bool
    refresh_token_set: bool
    webhook_secret_set: bool
    is_enabled: bool
    configuration_state: str
    validation_errors: list[str]
    operator_summary: str
    updated_at: datetime | None


@dataclass(slots=True)
class MarketingCampaignDetails:
    id: str
    tenant_id: str
    name: str
    channel: str
    audience_type: str
    audience_description: str | None
    target_company_id: str | None
    target_contact_id: str | None
    subject: str | None
    message_body: str
    status: str
    scheduled_for: datetime | None
    blocked_reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class MarketingCampaignListResult:
    items: list[MarketingCampaignDetails]
    total: int


@dataclass(slots=True)
class MarketingAudienceSummary:
    audience_type: str
    summary_label: str
    target_company_label: str | None
    target_contact_label: str | None
    total_contacts: int
    email_eligible_contacts: int
    blocked_reasons: list[str]


@dataclass(slots=True)
class MarketingSendReadiness:
    channel: str
    can_send: bool
    smtp_ready: bool
    queue_ready: bool
    blocked_reasons: list[str]
    capacity_note: str


@dataclass(slots=True)
class MarketingCampaignExecutionDetails:
    id: str
    tenant_id: str
    campaign_id: str
    channel: str
    status: str
    total_recipients: int
    processed_recipients: int
    sent_recipients: int
    failed_recipients: int
    batch_size: int
    queued_batch_count: int
    queue_job_id: str | None
    blocked_reason: str | None
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    snapshot: MarketingCampaignExecutionSnapshot | None


@dataclass(slots=True)
class MarketingCampaignExecutionSnapshot:
    audience_type: str
    summary_label: str
    target_company_label: str | None
    target_contact_label: str | None
    total_matched_records: int
    eligible_recipients: int
    excluded_recipients: int
    exclusion_counts: list["MarketingAudiencePreviewExclusionCount"]


@dataclass(slots=True)
class MarketingCampaignExecutionRecipientDetails:
    id: str
    execution_id: str
    campaign_id: str
    contact_id: str | None
    contact_name: str
    email: str
    phone: str | None
    first_name: str | None
    last_name: str | None
    company: str | None
    batch_number: int
    status: str
    failure_reason: str | None
    support_ticket_id: str | None
    handoff_at: datetime | None
    handoff_by_user_id: str | None
    handoff_status: str | None
    sent_at: datetime | None


@dataclass(slots=True)
class MarketingCampaignDetail:
    campaign: MarketingCampaignDetails
    audience_summary: MarketingAudienceSummary
    send_readiness: MarketingSendReadiness
    latest_execution: MarketingCampaignExecutionDetails | None
    latest_execution_snapshot: MarketingCampaignExecutionSnapshot | None
    execution_history: list[MarketingCampaignExecutionDetails]
    recent_recipients: list[MarketingCampaignExecutionRecipientDetails]


@dataclass(slots=True)
class MarketingAudiencePreviewExclusionCount:
    reason: str
    count: int


@dataclass(slots=True)
class MarketingAudiencePreviewRecipient:
    contact_id: str
    contact_name: str
    email: str | None
    phone: str | None
    company: str | None
    eligibility_status: str
    exclusion_reason: str | None


@dataclass(slots=True)
class MarketingCampaignAudiencePreview:
    campaign: MarketingCampaignDetails
    audience_summary: MarketingAudienceSummary
    send_readiness: MarketingSendReadiness
    total_matched_records: int
    eligible_recipients: int
    excluded_recipients: int
    exclusion_counts: list[MarketingAudiencePreviewExclusionCount]
    sample_limit: int
    has_more_recipients: bool
    recipients: list[MarketingAudiencePreviewRecipient]


@dataclass(slots=True)
class MarketingAudiencePreviewRecipientRecord:
    contact: ContactDetails
    preview: MarketingAudiencePreviewRecipient


@dataclass(slots=True)
class MarketingRecordReference:
    id: str
    label: str


@dataclass(slots=True)
class WhatsAppLeadIntakeResult:
    deal: MarketingRecordReference
    company: MarketingRecordReference
    contact: MarketingRecordReference | None
    campaign: MarketingRecordReference | None


@dataclass(slots=True)
class ContactImportPreviewRow:
    row_number: int
    full_name: str | None
    email: str | None
    phone: str | None
    company: str | None
    status: str
    message: str


@dataclass(slots=True)
class ContactImportPreviewResult:
    total_rows: int
    ready_rows: int
    skipped_rows: int
    error_rows: int
    rows: list[ContactImportPreviewRow]


@dataclass(slots=True)
class MarketingCampaignExecutionRecipientStatusCount:
    status: str
    count: int


@dataclass(slots=True)
class MarketingCampaignExecutionReadback:
    execution: MarketingCampaignExecutionDetails
    execution_snapshot: MarketingCampaignExecutionSnapshot | None
    recipient_filter: str
    recipient_counts: list[MarketingCampaignExecutionRecipientStatusCount]
    recipients: list[MarketingCampaignExecutionRecipientDetails]


@dataclass(slots=True)
class MarketingExecutionFollowUpHandoffResult:
    recipient_id: str
    contact_name: str
    email: str
    status: str
    support_ticket_id: str | None
    message: str | None


@dataclass(slots=True)
class MarketingExecutionFollowUpHandoffResponse:
    execution_id: str
    campaign_id: str
    requested_count: int
    created_count: int
    failed_count: int
    results: list[MarketingExecutionFollowUpHandoffResult]


def _load_json(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _dump_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_email(value: str | None) -> str | None:
    cleaned = _clean_optional(value)
    return cleaned.lower() if cleaned else None


def _normalize_campaign_audience_type(value: str | None) -> str:
    normalized = (_clean_optional(value) or "all_contacts").lower()
    if normalized not in ALLOWED_CAMPAIGN_AUDIENCE_TYPES:
        raise ValueError(
            "Invalid campaign audience type. Allowed values: "
            + ", ".join(ALLOWED_CAMPAIGN_AUDIENCE_TYPES)
        )
    return normalized


def _social_provider_state(
    provider: str,
    *,
    payload: dict[str, object],
) -> tuple[str, list[str]]:
    required = SOCIAL_PROVIDER_REQUIRED_FIELDS[provider]
    missing: list[str] = []
    for field in required:
        value = payload.get(field)
        if isinstance(value, str):
            present = bool(value.strip())
        else:
            present = value is not None
        if not present:
            missing.append(field)

    if len(missing) == len(required):
        return "not_configured", []
    if missing:
        return "incomplete", [f"Missing required field: {field}" for field in missing]
    return "configured", []


def _social_provider_from_payload(
    provider: str,
    *,
    payload: dict[str, object],
    updated_at: datetime | None,
) -> SocialIntegrationProviderDetails:
    configuration_state, validation_errors = _social_provider_state(provider, payload=payload)
    capability = SOCIAL_PROVIDER_CAPABILITIES[provider]
    return SocialIntegrationProviderDetails(
        provider=provider,
        display_name=capability.display_name,
        account_id=payload.get("account_id") if isinstance(payload.get("account_id"), str) else None,
        account_name=payload.get("account_name") if isinstance(payload.get("account_name"), str) else None,
        page_id=payload.get("page_id") if isinstance(payload.get("page_id"), str) else None,
        profile_id=payload.get("profile_id") if isinstance(payload.get("profile_id"), str) else None,
        access_token_set=bool(_clean_optional(payload.get("access_token") if isinstance(payload.get("access_token"), str) else None)),
        refresh_token_set=bool(_clean_optional(payload.get("refresh_token") if isinstance(payload.get("refresh_token"), str) else None)),
        webhook_secret_set=bool(_clean_optional(payload.get("webhook_secret") if isinstance(payload.get("webhook_secret"), str) else None)),
        is_enabled=bool(payload.get("is_enabled", False)),
        configuration_state=configuration_state,
        validation_errors=validation_errors,
        operator_summary=capability.operator_summary,
        updated_at=updated_at,
    )


def _normalize_campaign_channel(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_CAMPAIGN_CHANNELS:
        raise ValueError(
            "Invalid campaign channel. Allowed values: "
            + ", ".join(ALLOWED_CAMPAIGN_CHANNELS)
        )
    return normalized


def _normalize_campaign_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_CAMPAIGN_EDITABLE_STATUSES:
        raise ValueError(
            "Invalid campaign status. Allowed values: "
            + ", ".join(ALLOWED_CAMPAIGN_EDITABLE_STATUSES)
        )
    return normalized


def _normalize_execution_recipient_filter(value: str | None) -> str:
    normalized = (_clean_optional(value) or "all").lower()
    if normalized not in ALLOWED_EXECUTION_RECIPIENT_FILTERS:
        raise ValueError(
            "Invalid execution recipient filter. Allowed values: "
            + ", ".join(ALLOWED_EXECUTION_RECIPIENT_FILTERS)
        )
    return normalized


def _normalize_money_amount(value: str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Amount must be a valid decimal amount") from exc
    if normalized < 0:
        raise ValueError("Amount must be zero or greater")
    return normalized


def _normalize_currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("Currency must be a valid ISO 4217 uppercase 3-letter code")
    return normalized


def _raise_for_whatsapp_intake_integrity_error(exc: IntegrityError) -> None:
    message = str(exc.orig) if exc.orig is not None else str(exc)

    if "ck_deals_stage_valid" in message or "ck_deals_status_valid" in message:
        raise ValueError(
            "Lead intake could not create the linked deal because the sales stage/status contract "
            "is out of sync with persistence constraints. Run alembic upgrade head and retry."
        ) from exc

    if "uq_companies_tenant_name" in message:
        raise ValueError("A company with that name already exists for this tenant") from exc

    if "uq_contacts_tenant_email" in message:
        raise ValueError("A contact with that email already exists for this tenant") from exc

    if (
        "companies" in message
        or "contacts" in message
        or "deals" in message
        or "foreign key constraint" in message.lower()
    ):
        raise ValueError(
            "The selected CRM context could not be saved safely. Refresh the page and try again."
        ) from exc

    raise exc


async def _tenant_column_exists(session: AsyncSession, column_name: str) -> bool:
    result = await session.execute(
        text(
            """
            select exists (
                select 1
                from information_schema.columns
                where table_schema = 'public'
                  and table_name = 'tenants'
                  and column_name = :column_name
            ) as column_exists
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


async def _table_exists(session: AsyncSession, table_name: str) -> bool:
    result = await session.execute(
        text(
            """
            select exists (
                select 1
                from information_schema.tables
                where table_schema = 'public'
                  and table_name = :table_name
            ) as table_exists
            """
        ),
        {"table_name": table_name},
    )
    return bool(result.scalar())


async def _get_raw_tenant_settings(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> tuple[dict[str, object], dict[str, object], datetime | None]:
    result = await session.execute(
        text(
            """
            select
                updated_at,
                whatsapp_settings,
                smtp_settings
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Tenant not found")
    return (
        _load_json(row.get("whatsapp_settings")),
        _load_json(row.get("smtp_settings")),
        row.get("updated_at"),
    )


def _campaign_from_row(row: dict[str, object]) -> MarketingCampaignDetails:
    return MarketingCampaignDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        channel=str(row["channel"]),
        audience_type=str(row["audience_type"]),
        audience_description=row["audience_description"],
        target_company_id=row["target_company_id"],
        target_contact_id=row["target_contact_id"],
        subject=row["subject"],
        message_body=str(row["message_body"]),
        status=str(row["status"]),
        scheduled_for=row["scheduled_for"],
        blocked_reason=row.get("blocked_reason"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def _find_company_by_name(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_name: str,
) -> CompanyDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                name,
                website,
                email,
                phone,
                industry,
                address,
                vat_number,
                registration_number,
                notes,
                created_at,
                updated_at
            from public.companies
            where tenant_id = cast(:tenant_id as varchar)
              and lower(name) = lower(cast(:name as varchar))
            order by updated_at desc
            limit 1
            """
        ),
        {"tenant_id": tenant_id, "name": company_name},
    )
    row = result.mappings().first()
    if not row:
        return None
    return CompanyDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        website=row["website"],
        email=row["email"],
        phone=row["phone"],
        industry=row["industry"],
        address=row["address"],
        vat_number=row["vat_number"],
        registration_number=row["registration_number"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def _find_contact_by_phone_or_email(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    phone: str | None,
    email: str | None,
) -> ContactDetails | None:
    normalized_phone = _clean_optional(phone)
    normalized_email = _clean_optional(email)
    if normalized_phone is None and normalized_email is None:
        return None

    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                first_name,
                last_name,
                email,
                phone,
                company_id,
                company,
                job_title,
                notes,
                created_at,
                updated_at
            from public.contacts
            where tenant_id = cast(:tenant_id as varchar)
              and company_id = cast(:company_id as varchar)
              and (
                    (:phone is not null and phone = cast(:phone as varchar))
                 or (:email is not null and lower(coalesce(email, '')) = lower(cast(:email as varchar)))
              )
            order by updated_at desc
            limit 1
            """
        ),
        {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "phone": normalized_phone,
            "email": normalized_email,
        },
    )
    row = result.mappings().first()
    if not row:
        return None
    return ContactDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        first_name=str(row["first_name"]),
        last_name=row["last_name"],
        email=row["email"],
        phone=row["phone"],
        company_id=row["company_id"],
        company=row["company"],
        job_title=row["job_title"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def get_marketing_integrations(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> MarketingIntegrationsDetails:
    whatsapp_settings_exist = await _tenant_column_exists(session, "whatsapp_settings")
    smtp_settings_exist = await _tenant_column_exists(session, "smtp_settings")
    social_settings_exist = await _tenant_column_exists(session, "social_integration_settings")
    select_columns = ["id", "updated_at"]
    if whatsapp_settings_exist:
        select_columns.append("whatsapp_settings")
    if smtp_settings_exist:
        select_columns.append("smtp_settings")
    if social_settings_exist:
        select_columns.append("social_integration_settings")

    result = await session.execute(
        text(
            f"""
            select {", ".join(select_columns)}
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Tenant not found")

    whatsapp = _load_json(row.get("whatsapp_settings")) if whatsapp_settings_exist else {}
    smtp = _load_json(row.get("smtp_settings")) if smtp_settings_exist else {}
    social = _load_json(row.get("social_integration_settings")) if social_settings_exist else {}
    social_providers_payload = _load_json(social.get("providers"))
    updated_at = row.get("updated_at")

    return MarketingIntegrationsDetails(
        whatsapp=WhatsAppIntegrationDetails(
            business_account_id=whatsapp.get("business_account_id") or None,
            phone_number_id=whatsapp.get("phone_number_id") or None,
            display_name=whatsapp.get("display_name") or None,
            access_token_set=bool(whatsapp.get("access_token")),
            webhook_verify_token_set=bool(whatsapp.get("webhook_verify_token")),
            is_enabled=bool(whatsapp.get("is_enabled", False)),
            updated_at=updated_at,
        ),
        smtp=SmtpSettingsDetails(
            smtp_host=smtp.get("smtp_host") or None,
            smtp_port=int(smtp.get("smtp_port") or 587),
            smtp_username=smtp.get("smtp_username") or None,
            from_email=smtp.get("from_email") or None,
            from_name=smtp.get("from_name") or None,
            use_tls=bool(smtp.get("use_tls", True)),
            use_ssl=bool(smtp.get("use_ssl", False)),
            password_set=bool(smtp.get("smtp_password")),
            is_enabled=bool(smtp.get("is_enabled", False)),
            updated_at=updated_at,
        ),
        social=[
            _social_provider_from_payload(
                provider,
                payload=_load_json(social_providers_payload.get(provider)),
                updated_at=updated_at,
            )
            for provider in SUPPORTED_SOCIAL_PROVIDERS
        ],
    )


async def update_whatsapp_settings(
    session: AsyncSession,
    *,
    tenant_id: str,
    business_account_id: str | None,
    phone_number_id: str | None,
    display_name: str | None,
    access_token: str | None,
    webhook_verify_token: str | None,
    is_enabled: bool,
) -> WhatsAppIntegrationDetails:
    if not await _tenant_column_exists(session, "whatsapp_settings"):
        raise ValueError(
            "WhatsApp integration settings require the latest database migration. "
            "Run alembic upgrade head and retry."
        )

    _, _, _ = await _get_raw_tenant_settings(session, tenant_id=tenant_id)
    result = await session.execute(
        text(
            """
            select whatsapp_settings
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first() or {}
    existing = _load_json(row.get("whatsapp_settings"))
    next_settings = {
        "business_account_id": _clean_optional(business_account_id)
        if business_account_id is not None
        else existing.get("business_account_id"),
        "phone_number_id": _clean_optional(phone_number_id)
        if phone_number_id is not None
        else existing.get("phone_number_id"),
        "display_name": _clean_optional(display_name)
        if display_name is not None
        else existing.get("display_name"),
        "access_token": existing.get("access_token"),
        "webhook_verify_token": existing.get("webhook_verify_token"),
        "is_enabled": is_enabled,
    }
    if access_token is not None:
        next_settings["access_token"] = _clean_optional(access_token)
    if webhook_verify_token is not None:
        next_settings["webhook_verify_token"] = _clean_optional(webhook_verify_token)

    await session.execute(
        text(
            """
            update public.tenants
            set whatsapp_settings = cast(:whatsapp_settings as jsonb),
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "whatsapp_settings": _dump_json(next_settings)},
    )

    return (await get_marketing_integrations(session, tenant_id=tenant_id)).whatsapp


async def update_smtp_settings(
    session: AsyncSession,
    *,
    tenant_id: str,
    smtp_host: str | None,
    smtp_port: int,
    smtp_username: str | None,
    smtp_password: str | None,
    from_email: str | None,
    from_name: str | None,
    use_tls: bool,
    use_ssl: bool,
    is_enabled: bool,
) -> SmtpSettingsDetails:
    if not await _tenant_column_exists(session, "smtp_settings"):
        raise ValueError(
            "SMTP settings require the latest database migration. "
            "Run alembic upgrade head and retry."
        )

    result = await session.execute(
        text(
            """
            select smtp_settings
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first() or {}
    existing = _load_json(row.get("smtp_settings"))

    next_settings = {
        "smtp_host": _clean_optional(smtp_host) if smtp_host is not None else existing.get("smtp_host"),
        "smtp_port": smtp_port,
        "smtp_username": _clean_optional(smtp_username)
        if smtp_username is not None
        else existing.get("smtp_username"),
        "smtp_password": existing.get("smtp_password"),
        "from_email": _clean_optional(from_email) if from_email is not None else existing.get("from_email"),
        "from_name": _clean_optional(from_name) if from_name is not None else existing.get("from_name"),
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "is_enabled": is_enabled,
    }
    if smtp_password is not None:
        next_settings["smtp_password"] = _clean_optional(smtp_password)

    await session.execute(
        text(
            """
            update public.tenants
            set smtp_settings = cast(:smtp_settings as jsonb),
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "smtp_settings": _dump_json(next_settings)},
    )

    return (await get_marketing_integrations(session, tenant_id=tenant_id)).smtp


async def update_social_integration_provider(
    session: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    account_id: str | None,
    account_name: str | None,
    page_id: str | None,
    profile_id: str | None,
    access_token: str | None,
    refresh_token: str | None,
    webhook_secret: str | None,
    is_enabled: bool,
) -> SocialIntegrationProviderDetails:
    normalized_provider = (_clean_optional(provider) or "").lower()
    if normalized_provider not in SUPPORTED_SOCIAL_PROVIDERS:
        raise ValueError(
            "Unsupported social provider. Allowed values: "
            + ", ".join(SUPPORTED_SOCIAL_PROVIDERS)
        )

    if not await _tenant_column_exists(session, "social_integration_settings"):
        raise ValueError(
            "Social integration settings require the latest database migration. "
            "Run alembic upgrade head and retry."
        )

    result = await session.execute(
        text(
            """
            select social_integration_settings
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first() or {}
    existing = _load_json(row.get("social_integration_settings"))
    providers_payload = _load_json(existing.get("providers"))
    existing_provider_payload = _load_json(providers_payload.get(normalized_provider))

    next_provider_payload = {
        "account_id": _clean_optional(account_id) if account_id is not None else existing_provider_payload.get("account_id"),
        "account_name": _clean_optional(account_name) if account_name is not None else existing_provider_payload.get("account_name"),
        "page_id": _clean_optional(page_id) if page_id is not None else existing_provider_payload.get("page_id"),
        "profile_id": _clean_optional(profile_id) if profile_id is not None else existing_provider_payload.get("profile_id"),
        "access_token": existing_provider_payload.get("access_token"),
        "refresh_token": existing_provider_payload.get("refresh_token"),
        "webhook_secret": existing_provider_payload.get("webhook_secret"),
        "is_enabled": is_enabled,
    }
    if access_token is not None:
        next_provider_payload["access_token"] = _clean_optional(access_token)
    if refresh_token is not None:
        next_provider_payload["refresh_token"] = _clean_optional(refresh_token)
    if webhook_secret is not None:
        next_provider_payload["webhook_secret"] = _clean_optional(webhook_secret)

    providers_payload[normalized_provider] = next_provider_payload
    next_payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "providers": providers_payload,
    }

    await session.execute(
        text(
            """
            update public.tenants
            set social_integration_settings = cast(:social_integration_settings as jsonb),
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "social_integration_settings": _dump_json(next_payload),
        },
    )

    integrations = await get_marketing_integrations(session, tenant_id=tenant_id)
    for social_provider in integrations.social:
        if social_provider.provider == normalized_provider:
            return social_provider
    raise ValueError("Failed to load saved social provider settings")


async def test_smtp_connection(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> tuple[bool, str]:
    integrations = await get_marketing_integrations(session, tenant_id=tenant_id)
    smtp = integrations.smtp
    result = await session.execute(
        text(
            """
            select smtp_settings
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first() or {}
    smtp_config = _load_json(row.get("smtp_settings"))
    password = smtp_config.get("smtp_password")

    if not smtp.smtp_host:
        raise ValueError("SMTP host is required before testing the connection")
    if not smtp.smtp_port:
        raise ValueError("SMTP port is required before testing the connection")

    smtp_client = aiosmtplib.SMTP(
        hostname=smtp.smtp_host,
        port=int(smtp.smtp_port),
        use_tls=bool(smtp.use_ssl),
        start_tls=bool(smtp.use_tls and not smtp.use_ssl),
        timeout=10,
    )

    await smtp_client.connect()
    if smtp.smtp_username and password:
        await smtp_client.login(smtp.smtp_username, str(password))
    await smtp_client.quit()
    return True, "SMTP connection succeeded"


async def _list_campaign_contacts(
    session: AsyncSession,
    *,
    tenant_id: str,
    audience_type: str,
    target_company_id: str | None,
    target_contact_id: str | None,
) -> list[ContactDetails]:
    params: dict[str, object] = {"tenant_id": tenant_id}
    sql = """
        select
            id,
            tenant_id,
            first_name,
            last_name,
            email,
            phone,
            company_id,
            company,
            job_title,
            notes,
            created_at,
            updated_at
        from public.contacts
        where tenant_id = cast(:tenant_id as varchar)
    """

    if audience_type == "target_contact_only":
        if not target_contact_id:
            return []
        sql += " and id = cast(:contact_id as varchar) "
        params["contact_id"] = target_contact_id
    elif audience_type == "target_company_contacts":
        if not target_company_id:
            return []
        sql += " and company_id = cast(:company_id as varchar) "
        params["company_id"] = target_company_id

    sql += " order by created_at desc, id desc "
    rows = (await session.execute(text(sql), params)).mappings().all()
    return [
        ContactDetails(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            first_name=str(row["first_name"]),
            last_name=row["last_name"],
            email=row["email"],
            phone=row["phone"],
            company_id=row["company_id"],
            company=row["company"],
            job_title=row["job_title"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


async def _contact_email_exists(
    session: AsyncSession,
    *,
    tenant_id: str,
    email: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.contacts
            where tenant_id = cast(:tenant_id as varchar)
              and lower(coalesce(email, '')) = lower(cast(:email as varchar))
            limit 1
            """
        ),
        {"tenant_id": tenant_id, "email": email},
    )
    return result.scalar_one_or_none() == 1


async def _resolve_audience_summary(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign: MarketingCampaignDetails,
) -> MarketingAudienceSummary:
    target_company_label = None
    target_contact_label = None
    blocked_reasons: list[str] = []

    if campaign.target_company_id:
        company = await get_company_by_id(session, tenant_id=tenant_id, company_id=str(campaign.target_company_id))
        target_company_label = company.name if company else None
    if campaign.target_contact_id:
        contact = await get_contact_by_id(session, tenant_id=tenant_id, contact_id=str(campaign.target_contact_id))
        if contact:
            target_contact_label = " ".join(
                part for part in [contact.first_name, contact.last_name] if part
            ).strip() or contact.email or contact.phone or contact.id

    contacts = await _list_campaign_contacts(
        session,
        tenant_id=tenant_id,
        audience_type=campaign.audience_type,
        target_company_id=campaign.target_company_id,
        target_contact_id=campaign.target_contact_id,
    )
    email_eligible_contacts = [contact for contact in contacts if _normalize_email(contact.email)]

    if campaign.audience_type == "target_contact_only" and not campaign.target_contact_id:
        blocked_reasons.append("Select a target contact for this audience.")
    if campaign.audience_type == "target_company_contacts" and not campaign.target_company_id:
        blocked_reasons.append("Select a target company for this audience.")
    if not contacts:
        blocked_reasons.append("No contacts match the current audience selection.")
    if campaign.channel == "email" and not email_eligible_contacts:
        blocked_reasons.append("No audience contacts currently have an email address.")

    summary_label = {
        "all_contacts": "All contacts in the current tenant",
        "target_company_contacts": (
            f"Contacts at {target_company_label}" if target_company_label else "Contacts at the selected company"
        ),
        "target_contact_only": (
            target_contact_label if target_contact_label else "Single target contact"
        ),
    }[campaign.audience_type]

    return MarketingAudienceSummary(
        audience_type=campaign.audience_type,
        summary_label=summary_label,
        target_company_label=target_company_label,
        target_contact_label=target_contact_label,
        total_contacts=len(contacts),
        email_eligible_contacts=len(email_eligible_contacts),
        blocked_reasons=blocked_reasons,
    )


async def _build_send_readiness(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign: MarketingCampaignDetails,
    queue_ready: bool,
    audience_summary: MarketingAudienceSummary | None = None,
) -> MarketingSendReadiness:
    resolved_audience_summary = audience_summary or await _resolve_audience_summary(
        session,
        tenant_id=tenant_id,
        campaign=campaign,
    )
    blocked_reasons = list(resolved_audience_summary.blocked_reasons)
    integrations = await get_marketing_integrations(session, tenant_id=tenant_id)
    smtp_ready = (
        integrations.smtp.is_enabled
        and bool(integrations.smtp.smtp_host)
        and bool(integrations.smtp.from_email)
        and integrations.smtp.password_set
    )

    if campaign.channel != "email":
        blocked_reasons.append("Only email campaigns have an execution foundation in this slice.")
    if not smtp_ready:
        blocked_reasons.append("SMTP must be configured and enabled before email campaigns can send.")
    if campaign.status == "scheduled" and campaign.scheduled_for and campaign.scheduled_for > datetime.now(UTC):
        blocked_reasons.append("Scheduled campaigns cannot send before their scheduled time.")
    if campaign.status == "sending":
        blocked_reasons.append("This campaign is already sending.")
    if campaign.status == "completed":
        blocked_reasons.append("Completed campaigns are protected from duplicate replay in this slice.")
    if not queue_ready:
        blocked_reasons.append("Background worker queue is unavailable, so bulk email dispatch is blocked.")

    return MarketingSendReadiness(
        channel=campaign.channel,
        can_send=len(blocked_reasons) == 0,
        smtp_ready=smtp_ready,
        queue_ready=queue_ready,
        blocked_reasons=blocked_reasons,
        capacity_note=EMAIL_CAMPAIGN_CAPACITY_NOTE,
    )


def _contact_display_name(contact: ContactDetails) -> str:
    return (
        " ".join(part for part in [contact.first_name, contact.last_name] if part).strip()
        or contact.email
        or contact.phone
        or contact.id
    )


def _channel_contact_method(
    *,
    channel: str,
    contact: ContactDetails,
) -> str | None:
    if channel == "email":
        return _normalize_email(contact.email)
    if channel == "whatsapp":
        return _clean_optional(contact.phone)
    return None


def _contact_excluded_by_target_context(
    *,
    campaign: MarketingCampaignDetails,
    contact: ContactDetails,
) -> bool:
    if campaign.audience_type == "target_company_contacts":
        return bool(campaign.target_company_id) and contact.company_id != campaign.target_company_id
    if campaign.audience_type == "target_contact_only":
        return bool(campaign.target_contact_id) and contact.id != campaign.target_contact_id
    return False


async def _build_campaign_audience_preview_recipient_records(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign: MarketingCampaignDetails,
) -> list[MarketingAudiencePreviewRecipientRecord]:
    contacts = await _list_campaign_contacts(
        session,
        tenant_id=tenant_id,
        audience_type=campaign.audience_type,
        target_company_id=campaign.target_company_id,
        target_contact_id=campaign.target_contact_id,
    )
    seen_contact_methods: set[str] = set()
    recipients: list[MarketingAudiencePreviewRecipientRecord] = []

    for contact in contacts:
        exclusion_reason: str | None = None
        eligibility_status = "eligible"
        contact_method = _channel_contact_method(channel=campaign.channel, contact=contact)

        if _contact_excluded_by_target_context(campaign=campaign, contact=contact):
            eligibility_status = "excluded_by_target_context"
            exclusion_reason = "Excluded by the current campaign target context."
        elif campaign.channel == "email" and not contact_method:
            eligibility_status = "missing_email"
            exclusion_reason = "Missing email address."
        elif campaign.channel == "whatsapp" and not contact_method:
            eligibility_status = "missing_phone"
            exclusion_reason = "Missing phone number."
        elif contact_method and contact_method in seen_contact_methods:
            eligibility_status = "duplicate_contact_method"
            exclusion_reason = "Duplicate contact method in this campaign preview."

        if contact_method and eligibility_status == "eligible":
            seen_contact_methods.add(contact_method)

        recipients.append(
            MarketingAudiencePreviewRecipientRecord(
                contact=contact,
                preview=MarketingAudiencePreviewRecipient(
                contact_id=contact.id,
                contact_name=_contact_display_name(contact),
                email=_normalize_email(contact.email),
                phone=_clean_optional(contact.phone),
                company=_clean_optional(contact.company),
                eligibility_status=eligibility_status,
                exclusion_reason=exclusion_reason,
                ),
            )
        )

    return recipients


def _build_audience_preview_exclusion_counts(
    recipients: list[MarketingAudiencePreviewRecipient],
) -> list[MarketingAudiencePreviewExclusionCount]:
    counts: dict[str, int] = {}
    for recipient in recipients:
        if recipient.eligibility_status == "eligible":
            continue
        counts[recipient.eligibility_status] = counts.get(recipient.eligibility_status, 0) + 1

    ordered_reasons = [
        reason
        for reason in ALLOWED_AUDIENCE_PREVIEW_RECIPIENT_STATUSES
        if reason != "eligible" and reason in counts
    ]
    return [
        MarketingAudiencePreviewExclusionCount(reason=reason, count=counts[reason])
        for reason in ordered_reasons
    ]


def _build_execution_snapshot(
    *,
    audience_summary: MarketingAudienceSummary,
    total_matched_records: int,
    eligible_recipients: int,
    exclusion_counts: list[MarketingAudiencePreviewExclusionCount],
) -> MarketingCampaignExecutionSnapshot:
    return MarketingCampaignExecutionSnapshot(
        audience_type=audience_summary.audience_type,
        summary_label=audience_summary.summary_label,
        target_company_label=audience_summary.target_company_label,
        target_contact_label=audience_summary.target_contact_label,
        total_matched_records=total_matched_records,
        eligible_recipients=eligible_recipients,
        excluded_recipients=max(total_matched_records - eligible_recipients, 0),
        exclusion_counts=exclusion_counts,
    )


def _execution_snapshot_to_metadata(
    snapshot: MarketingCampaignExecutionSnapshot | None,
) -> dict[str, object]:
    if snapshot is None:
        return {}

    return {
        "audience_snapshot": {
            "audience_type": snapshot.audience_type,
            "summary_label": snapshot.summary_label,
            "target_company_label": snapshot.target_company_label,
            "target_contact_label": snapshot.target_contact_label,
            "total_matched_records": snapshot.total_matched_records,
            "eligible_recipients": snapshot.eligible_recipients,
            "excluded_recipients": snapshot.excluded_recipients,
            "exclusion_counts": [
                {"reason": item.reason, "count": item.count}
                for item in snapshot.exclusion_counts
            ],
        }
    }


def _execution_snapshot_from_metadata(
    metadata: dict[str, object],
) -> MarketingCampaignExecutionSnapshot | None:
    snapshot_payload = _load_json(metadata.get("audience_snapshot"))
    if not snapshot_payload:
        return None

    audience_type = snapshot_payload.get("audience_type")
    summary_label = snapshot_payload.get("summary_label")
    total_matched_records = snapshot_payload.get("total_matched_records")
    eligible_recipients = snapshot_payload.get("eligible_recipients")
    excluded_recipients = snapshot_payload.get("excluded_recipients")
    exclusion_counts_payload = snapshot_payload.get("exclusion_counts")

    if not isinstance(audience_type, str) or not isinstance(summary_label, str):
        return None
    if not isinstance(total_matched_records, int) or not isinstance(eligible_recipients, int):
        return None
    if not isinstance(excluded_recipients, int):
        return None

    exclusion_counts: list[MarketingAudiencePreviewExclusionCount] = []
    if isinstance(exclusion_counts_payload, list):
        for item in exclusion_counts_payload:
            if not isinstance(item, dict):
                continue
            reason = item.get("reason")
            count = item.get("count")
            if isinstance(reason, str) and isinstance(count, int):
                exclusion_counts.append(
                    MarketingAudiencePreviewExclusionCount(reason=reason, count=count)
                )

    return MarketingCampaignExecutionSnapshot(
        audience_type=audience_type,
        summary_label=summary_label,
        target_company_label=(
            snapshot_payload.get("target_company_label")
            if isinstance(snapshot_payload.get("target_company_label"), str)
            else None
        ),
        target_contact_label=(
            snapshot_payload.get("target_contact_label")
            if isinstance(snapshot_payload.get("target_contact_label"), str)
            else None
        ),
        total_matched_records=total_matched_records,
        eligible_recipients=eligible_recipients,
        excluded_recipients=excluded_recipients,
        exclusion_counts=exclusion_counts,
    )


def _execution_from_row(row: dict[str, object]) -> MarketingCampaignExecutionDetails:
    metadata = _load_json(row.get("metadata"))
    return MarketingCampaignExecutionDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        campaign_id=str(row["campaign_id"]),
        channel=str(row["channel"]),
        status=str(row["status"]),
        total_recipients=int(row["total_recipients"] or 0),
        processed_recipients=int(row["processed_recipients"] or 0),
        sent_recipients=int(row["sent_recipients"] or 0),
        failed_recipients=int(row["failed_recipients"] or 0),
        batch_size=int(row["batch_size"] or EMAIL_CAMPAIGN_BATCH_SIZE),
        queued_batch_count=int(row["queued_batch_count"] or 0),
        queue_job_id=row["queue_job_id"],
        blocked_reason=row["blocked_reason"],
        requested_at=row["requested_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        snapshot=_execution_snapshot_from_metadata(metadata),
    )


def _build_execution_recipient_contact_name(
    *,
    first_name: str | None,
    last_name: str | None,
    email: str,
) -> str:
    contact_name = " ".join(part for part in [first_name, last_name] if part).strip()
    return contact_name or email


def _execution_recipient_from_row(row: dict[str, object]) -> MarketingCampaignExecutionRecipientDetails:
    email = str(row["email"])
    first_name = row["first_name"] if isinstance(row["first_name"], str) else None
    last_name = row["last_name"] if isinstance(row["last_name"], str) else None
    return MarketingCampaignExecutionRecipientDetails(
        id=str(row["id"]),
        execution_id=str(row["execution_id"]),
        campaign_id=str(row["campaign_id"]),
        contact_id=row["contact_id"],
        contact_name=_build_execution_recipient_contact_name(
            first_name=first_name,
            last_name=last_name,
            email=email,
        ),
        email=email,
        phone=row["phone"] if isinstance(row.get("phone"), str) else None,
        first_name=first_name,
        last_name=last_name,
        company=row["company"],
        batch_number=int(row["batch_number"] or 1),
        status=str(row["status"]),
        failure_reason=row["failure_reason"],
        support_ticket_id=row["support_ticket_id"] if isinstance(row.get("support_ticket_id"), str) else None,
        handoff_at=row["handoff_at"],
        handoff_by_user_id=row["handoff_by_user_id"] if isinstance(row.get("handoff_by_user_id"), str) else None,
        handoff_status=row["handoff_status"] if isinstance(row.get("handoff_status"), str) else None,
        sent_at=row["sent_at"],
    )


async def get_marketing_campaign_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> MarketingCampaignDetails | None:
    if not await _table_exists(session, "marketing_campaigns"):
        raise ValueError(
            "Marketing campaigns require the latest database migration. "
            "Run alembic upgrade head and retry."
        )

    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                name,
                channel,
                audience_type,
                audience_description,
                target_company_id,
                target_contact_id,
                subject,
                message_body,
                status,
                scheduled_for,
                blocked_reason,
                created_at,
                updated_at
            from public.marketing_campaigns
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:campaign_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "campaign_id": campaign_id},
    )
    row = result.mappings().first()
    if not row:
        return None
    return _campaign_from_row(row)


async def _validate_campaign_target_context(
    session: AsyncSession,
    *,
    tenant_id: str,
    audience_type: str,
    target_company_id: str | None,
    target_contact_id: str | None,
) -> tuple[str | None, str | None]:
    normalized_company_id = _clean_optional(target_company_id)
    normalized_contact_id = _clean_optional(target_contact_id)

    company = None
    if normalized_company_id is not None:
        company = await get_company_by_id(session, tenant_id=tenant_id, company_id=normalized_company_id)
        if company is None:
            raise ValueError("Campaign target company does not exist")

    if normalized_contact_id is not None:
        contact = await get_contact_by_id(session, tenant_id=tenant_id, contact_id=normalized_contact_id)
        if contact is None:
            raise ValueError("Campaign target contact does not exist")
        if company is not None and contact.company_id != company.id:
            raise ValueError("Campaign target contact does not belong to the selected company")

    if audience_type == "target_company_contacts" and normalized_company_id is None:
        raise ValueError("Campaign audience requires a target company")
    if audience_type == "target_contact_only" and normalized_contact_id is None:
        raise ValueError("Campaign audience requires a target contact")
    if audience_type == "all_contacts" and (normalized_company_id is not None or normalized_contact_id is not None):
        raise ValueError("All contacts audience cannot pin a single target company or contact")

    return normalized_company_id, normalized_contact_id


def _validate_campaign_content(
    *,
    channel: str,
    subject: str | None,
    message_body: str,
    status: str,
    scheduled_for: datetime | None,
) -> tuple[str | None, str, datetime | None]:
    normalized_subject = _clean_optional(subject)
    normalized_message_body = message_body.strip()
    if not normalized_message_body:
        raise ValueError("Campaign message body is required")
    if channel == "email" and normalized_subject is None:
        raise ValueError("Email campaigns require a subject")
    if status == "scheduled" and scheduled_for is None:
        raise ValueError("Scheduled campaigns require a scheduled time")
    if status == "draft":
        scheduled_for = None
    return normalized_subject, normalized_message_body, scheduled_for


async def list_marketing_campaigns(
    session: AsyncSession,
    *,
    tenant_id: str,
    q: str | None = None,
    channel: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> MarketingCampaignListResult:
    if not await _table_exists(session, "marketing_campaigns"):
        raise ValueError(
            "Marketing campaigns require the latest database migration. "
            "Run alembic upgrade head and retry."
        )

    search = _clean_optional(q)
    normalized_channel = _normalize_campaign_channel(channel) if channel else None
    normalized_status = (_clean_optional(status) or "").lower() if status else None
    if normalized_status and normalized_status not in ALLOWED_CAMPAIGN_STATUSES:
        raise ValueError(
            "Invalid campaign status. Allowed values: " + ", ".join(ALLOWED_CAMPAIGN_STATUSES)
        )

    count_sql = """
        select count(*)
        from public.marketing_campaigns
        where tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            id,
            tenant_id,
            name,
            channel,
            audience_type,
            audience_description,
            target_company_id,
            target_contact_id,
            subject,
            message_body,
            status,
            scheduled_for,
            blocked_reason,
            created_at,
            updated_at
        from public.marketing_campaigns
        where tenant_id = cast(:tenant_id as varchar)
    """
    params: dict[str, object] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

    if search:
        clause = """
          and (
                lower(name) like :search
             or lower(coalesce(audience_description, '')) like :search
             or lower(coalesce(subject, '')) like :search
             or lower(message_body) like :search
          )
        """
        count_sql += clause
        list_sql += clause
        params["search"] = f"%{search.lower()}%"

    if normalized_channel:
        clause = " and channel = cast(:channel as varchar) "
        count_sql += clause
        list_sql += clause
        params["channel"] = normalized_channel

    if normalized_status:
        clause = " and status = cast(:status as varchar) "
        count_sql += clause
        list_sql += clause
        params["status"] = normalized_status

    list_sql += """
        order by updated_at desc, id desc
        limit :limit
        offset :offset
    """

    total = int((await session.execute(text(count_sql), params)).scalar_one())
    rows = (await session.execute(text(list_sql), params)).mappings().all()

    return MarketingCampaignListResult(
        items=[_campaign_from_row(row) for row in rows],
        total=total,
    )


async def create_marketing_campaign(
    session: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    channel: str,
    audience_type: str,
    audience_description: str | None,
    target_company_id: str | None,
    target_contact_id: str | None,
    subject: str | None,
    message_body: str,
    status: str,
    scheduled_for: datetime | None,
) -> MarketingCampaignDetails:
    if not await _table_exists(session, "marketing_campaigns"):
        raise ValueError(
            "Marketing campaigns require the latest database migration. "
            "Run alembic upgrade head and retry."
        )

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Campaign name is required")

    normalized_channel = _normalize_campaign_channel(channel)
    normalized_status = _normalize_campaign_status(status)
    normalized_audience_type = _normalize_campaign_audience_type(audience_type)
    normalized_company_id, normalized_contact_id = await _validate_campaign_target_context(
        session,
        tenant_id=tenant_id,
        audience_type=normalized_audience_type,
        target_company_id=target_company_id,
        target_contact_id=target_contact_id,
    )
    normalized_subject, normalized_message_body, normalized_scheduled_for = _validate_campaign_content(
        channel=normalized_channel,
        subject=subject,
        message_body=message_body,
        status=normalized_status,
        scheduled_for=scheduled_for,
    )

    campaign_id = str(uuid.uuid4())
    result = await session.execute(
        text(
            """
            insert into public.marketing_campaigns (
                id,
                tenant_id,
                name,
                channel,
                audience_type,
                audience_description,
                target_company_id,
                target_contact_id,
                subject,
                message_body,
                status,
                scheduled_for
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:name as varchar),
                cast(:channel as varchar),
                cast(:audience_type as varchar),
                :audience_description,
                cast(:target_company_id as varchar),
                cast(:target_contact_id as varchar),
                cast(:subject as varchar),
                :message_body,
                cast(:status as varchar),
                :scheduled_for
            )
            returning
                id,
                tenant_id,
                name,
                channel,
                audience_type,
                audience_description,
                target_company_id,
                target_contact_id,
                subject,
                message_body,
                status,
                scheduled_for,
                blocked_reason,
                created_at,
                updated_at
            """
        ),
        {
            "id": campaign_id,
            "tenant_id": tenant_id,
            "name": normalized_name,
            "channel": normalized_channel,
            "audience_type": normalized_audience_type,
            "audience_description": _clean_optional(audience_description),
            "target_company_id": normalized_company_id,
            "target_contact_id": normalized_contact_id,
            "subject": normalized_subject,
            "message_body": normalized_message_body,
            "status": normalized_status,
            "scheduled_for": normalized_scheduled_for,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create campaign")
    return _campaign_from_row(row)


async def update_marketing_campaign(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    name: str,
    channel: str,
    audience_type: str,
    audience_description: str | None,
    target_company_id: str | None,
    target_contact_id: str | None,
    subject: str | None,
    message_body: str,
    status: str,
    scheduled_for: datetime | None,
) -> MarketingCampaignDetails:
    existing = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if existing is None:
        raise ValueError("Campaign does not exist")

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Campaign name is required")
    if existing.status in {"sending", "completed"}:
        raise ValueError("Sending or completed campaigns cannot be edited in this slice")

    normalized_channel = _normalize_campaign_channel(channel)
    normalized_status = _normalize_campaign_status(status)
    normalized_audience_type = _normalize_campaign_audience_type(audience_type)
    normalized_company_id, normalized_contact_id = await _validate_campaign_target_context(
        session,
        tenant_id=tenant_id,
        audience_type=normalized_audience_type,
        target_company_id=target_company_id,
        target_contact_id=target_contact_id,
    )
    normalized_subject, normalized_message_body, normalized_scheduled_for = _validate_campaign_content(
        channel=normalized_channel,
        subject=subject,
        message_body=message_body,
        status=normalized_status,
        scheduled_for=scheduled_for,
    )

    result = await session.execute(
        text(
            """
            update public.marketing_campaigns
            set name = cast(:name as varchar),
                channel = cast(:channel as varchar),
                audience_type = cast(:audience_type as varchar),
                audience_description = :audience_description,
                target_company_id = cast(:target_company_id as varchar),
                target_contact_id = cast(:target_contact_id as varchar),
                subject = cast(:subject as varchar),
                message_body = :message_body,
                status = cast(:status as varchar),
                scheduled_for = :scheduled_for,
                blocked_reason = null,
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:campaign_id as varchar)
            returning
                id,
                tenant_id,
                name,
                channel,
                audience_type,
                audience_description,
                target_company_id,
                target_contact_id,
                subject,
                message_body,
                status,
                scheduled_for,
                blocked_reason,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "name": normalized_name,
            "channel": normalized_channel,
            "audience_type": normalized_audience_type,
            "audience_description": _clean_optional(audience_description),
            "target_company_id": normalized_company_id,
            "target_contact_id": normalized_contact_id,
            "subject": normalized_subject,
            "message_body": normalized_message_body,
            "status": normalized_status,
            "scheduled_for": normalized_scheduled_for,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Campaign does not exist")
    return _campaign_from_row(row)


async def _get_latest_campaign_execution(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> MarketingCampaignExecutionDetails | None:
    executions = await _list_campaign_executions(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        limit=1,
    )
    return executions[0] if executions else None


async def _list_campaign_executions(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    limit: int | None = MARKETING_EXECUTION_HISTORY_DEFAULT_LIMIT,
) -> list[MarketingCampaignExecutionDetails]:
    if not await _table_exists(session, "marketing_campaign_executions"):
        return []

    query = """
        select
            id,
            tenant_id,
            campaign_id,
            channel,
            status,
            total_recipients,
            processed_recipients,
            sent_recipients,
            failed_recipients,
            batch_size,
            queued_batch_count,
            queue_job_id,
            blocked_reason,
            metadata,
            requested_at,
            started_at,
            completed_at,
            created_at,
            updated_at
        from public.marketing_campaign_executions
        where tenant_id = cast(:tenant_id as varchar)
          and campaign_id = cast(:campaign_id as varchar)
        order by requested_at desc, created_at desc, id desc
    """
    params: dict[str, object] = {"tenant_id": tenant_id, "campaign_id": campaign_id}
    if limit is not None:
        query += "\n        limit :limit"
        params["limit"] = limit

    rows = (await session.execute(text(query), params)).mappings().all()
    return [_execution_from_row(row) for row in rows]


async def _get_campaign_execution_by_id(
    session: AsyncSession,
    *,
    execution_id: str,
    tenant_id: str | None = None,
    campaign_id: str | None = None,
) -> MarketingCampaignExecutionDetails | None:
    if not await _table_exists(session, "marketing_campaign_executions"):
        return None

    query = """
        select
            id,
            tenant_id,
            campaign_id,
            channel,
            status,
            total_recipients,
            processed_recipients,
            sent_recipients,
            failed_recipients,
            batch_size,
            queued_batch_count,
            queue_job_id,
            blocked_reason,
            metadata,
            requested_at,
            started_at,
            completed_at,
            created_at,
            updated_at
        from public.marketing_campaign_executions
        where id = cast(:execution_id as varchar)
    """
    params: dict[str, object] = {"execution_id": execution_id}
    if tenant_id is not None:
        query += "\n          and tenant_id = cast(:tenant_id as varchar)"
        params["tenant_id"] = tenant_id
    if campaign_id is not None:
        query += "\n          and campaign_id = cast(:campaign_id as varchar)"
        params["campaign_id"] = campaign_id

    result = await session.execute(
        text(query),
        params,
    )
    row = result.mappings().first()
    return _execution_from_row(row) if row else None


async def _list_execution_recipients(
    session: AsyncSession,
    *,
    tenant_id: str,
    execution_id: str,
    limit: int | None = 20,
) -> list[MarketingCampaignExecutionRecipientDetails]:
    if not await _table_exists(session, "marketing_campaign_execution_recipients"):
        return []

    query = """
        select
            id,
            execution_id,
            campaign_id,
            contact_id,
            support_ticket_id,
            email,
            phone,
            first_name,
            last_name,
            company,
            batch_number,
            status,
            failure_reason,
            handoff_at,
            handoff_by_user_id,
            handoff_status,
            sent_at
        from public.marketing_campaign_execution_recipients
        where tenant_id = cast(:tenant_id as varchar)
          and execution_id = cast(:execution_id as varchar)
        order by batch_number asc, email asc
    """
    params: dict[str, object] = {"tenant_id": tenant_id, "execution_id": execution_id}
    if limit is not None:
        query += "\n        limit :limit"
        params["limit"] = limit

    rows = (await session.execute(text(query), params)).mappings().all()
    return [_execution_recipient_from_row(row) for row in rows]


async def get_marketing_campaign_detail(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    queue_ready: bool = True,
) -> MarketingCampaignDetail:
    campaign = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if campaign is None:
        raise ValueError("Campaign does not exist")

    audience_summary = await _resolve_audience_summary(session, tenant_id=tenant_id, campaign=campaign)
    send_readiness = await _build_send_readiness(
        session,
        tenant_id=tenant_id,
        campaign=campaign,
        queue_ready=queue_ready,
        audience_summary=audience_summary,
    )
    execution_history = await _list_campaign_executions(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
    )
    latest_execution = execution_history[0] if execution_history else None
    recent_recipients = (
        await _list_execution_recipients(session, tenant_id=tenant_id, execution_id=latest_execution.id)
        if latest_execution
        else []
    )
    return MarketingCampaignDetail(
        campaign=campaign,
        audience_summary=audience_summary,
        send_readiness=send_readiness,
        latest_execution=latest_execution,
        latest_execution_snapshot=latest_execution.snapshot if latest_execution else None,
        execution_history=execution_history,
        recent_recipients=recent_recipients,
    )


def _build_execution_recipient_status_counts(
    recipients: list[MarketingCampaignExecutionRecipientDetails],
) -> list[MarketingCampaignExecutionRecipientStatusCount]:
    status_counts = {
        "all": len(recipients),
        "failed": sum(1 for recipient in recipients if recipient.status == "failed"),
        "sent": sum(1 for recipient in recipients if recipient.status == "sent"),
        "pending": sum(1 for recipient in recipients if recipient.status == "pending"),
        "blocked": sum(1 for recipient in recipients if recipient.status == "blocked"),
    }
    return [
        MarketingCampaignExecutionRecipientStatusCount(status=status, count=count)
        for status, count in status_counts.items()
    ]


async def list_marketing_campaign_executions(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    limit: int = MARKETING_EXECUTION_HISTORY_DEFAULT_LIMIT,
) -> list[MarketingCampaignExecutionDetails]:
    campaign = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if campaign is None:
        raise ValueError("Campaign does not exist")

    return await _list_campaign_executions(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        limit=max(1, limit),
    )


async def get_marketing_campaign_execution_readback(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    execution_id: str,
    recipient_filter: str = "all",
) -> MarketingCampaignExecutionReadback:
    campaign = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if campaign is None:
        raise ValueError("Campaign does not exist")

    normalized_filter = _normalize_execution_recipient_filter(recipient_filter)
    execution = await _get_campaign_execution_by_id(
        session,
        execution_id=execution_id,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
    )
    if execution is None:
        raise ValueError("Campaign execution does not exist")

    recipients = await _list_execution_recipients(
        session,
        tenant_id=tenant_id,
        execution_id=execution.id,
        limit=None,
    )
    filtered_recipients = (
        recipients
        if normalized_filter == "all"
        else [recipient for recipient in recipients if recipient.status == normalized_filter]
    )
    return MarketingCampaignExecutionReadback(
        execution=execution,
        execution_snapshot=execution.snapshot,
        recipient_filter=normalized_filter,
        recipient_counts=_build_execution_recipient_status_counts(recipients),
        recipients=filtered_recipients,
    )


async def get_marketing_campaign_audience_preview(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    sample_limit: int = MARKETING_AUDIENCE_PREVIEW_DEFAULT_LIMIT,
    queue_ready: bool = True,
) -> MarketingCampaignAudiencePreview:
    campaign = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if campaign is None:
        raise ValueError("Campaign does not exist")

    effective_sample_limit = max(1, sample_limit)
    audience_summary = await _resolve_audience_summary(session, tenant_id=tenant_id, campaign=campaign)
    send_readiness = await _build_send_readiness(
        session,
        tenant_id=tenant_id,
        campaign=campaign,
        queue_ready=queue_ready,
        audience_summary=audience_summary,
    )
    recipient_records = await _build_campaign_audience_preview_recipient_records(
        session,
        tenant_id=tenant_id,
        campaign=campaign,
    )
    recipients = [record.preview for record in recipient_records]
    eligible_recipients = sum(1 for recipient in recipients if recipient.eligibility_status == "eligible")
    exclusion_counts = _build_audience_preview_exclusion_counts(recipients)

    return MarketingCampaignAudiencePreview(
        campaign=campaign,
        audience_summary=audience_summary,
        send_readiness=send_readiness,
        total_matched_records=len(recipients),
        eligible_recipients=eligible_recipients,
        excluded_recipients=len(recipients) - eligible_recipients,
        exclusion_counts=exclusion_counts,
        sample_limit=effective_sample_limit,
        has_more_recipients=len(recipients) > effective_sample_limit,
        recipients=recipients[:effective_sample_limit],
    )


async def export_marketing_campaign_audience_preview_csv(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> tuple[str, int]:
    campaign = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if campaign is None:
        raise ValueError("Campaign does not exist")

    recipient_records = await _build_campaign_audience_preview_recipient_records(
        session,
        tenant_id=tenant_id,
        campaign=campaign,
    )
    recipients = [record.preview for record in recipient_records]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "contact_name",
            "email",
            "phone",
            "company",
            "eligibility_status",
            "exclusion_reason",
        ]
    )
    for recipient in recipients:
        writer.writerow(
            [
                recipient.contact_name,
                recipient.email or "",
                recipient.phone or "",
                recipient.company or "",
                recipient.eligibility_status,
                recipient.exclusion_reason or "",
            ]
        )

    return output.getvalue(), len(recipients)


async def export_marketing_campaign_execution_results_csv(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    execution_id: str,
    recipient_filter: str = "all",
) -> tuple[str, int]:
    readback = await get_marketing_campaign_execution_readback(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        execution_id=execution_id,
        recipient_filter=recipient_filter,
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "execution_id",
            "campaign_id",
            "contact_name",
            "email",
            "phone",
            "company",
            "status",
            "failure_reason",
            "support_ticket_id",
            "sent_at",
            "batch_number",
        ]
    )
    for recipient in readback.recipients:
        writer.writerow(
            [
                readback.execution.id,
                readback.execution.campaign_id,
                recipient.contact_name,
                recipient.email,
                recipient.phone or "",
                recipient.company or "",
                recipient.status,
                recipient.failure_reason or "",
                recipient.support_ticket_id or "",
                recipient.sent_at.isoformat() if recipient.sent_at else "",
                recipient.batch_number,
            ]
        )

    return output.getvalue(), len(readback.recipients)


def _build_failed_recipient_follow_up_ticket_title(
    *,
    campaign_name: str,
    recipient: MarketingCampaignExecutionRecipientDetails,
) -> str:
    return f"Marketing follow-up: {campaign_name} failed recipient {recipient.contact_name}"


def _build_failed_recipient_follow_up_ticket_description(
    *,
    campaign_name: str,
    execution_id: str,
    recipient: MarketingCampaignExecutionRecipientDetails,
) -> str:
    lines = [
        "Marketing execution failed recipient follow-up",
        f"Campaign: {campaign_name}",
        f"Execution ID: {execution_id}",
        f"Recipient: {recipient.contact_name}",
        f"Email: {recipient.email}",
        f"Phone: {recipient.phone or 'Not recorded'}",
        f"Company: {recipient.company or 'Not recorded'}",
        f"Failure reason: {recipient.failure_reason or 'Not recorded'}",
    ]
    return "\n".join(lines)


async def create_failed_execution_recipient_follow_up_handoff(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    execution_id: str,
    recipient_ids: list[str],
    priority: str = "high",
    handoff_by_user_id: str | None = None,
) -> MarketingExecutionFollowUpHandoffResponse:
    campaign = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if campaign is None:
        raise ValueError("Campaign does not exist")

    execution = await _get_campaign_execution_by_id(
        session,
        execution_id=execution_id,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
    )
    if execution is None:
        raise ValueError("Campaign execution does not exist")

    normalized_ids = [recipient_id.strip() for recipient_id in recipient_ids if recipient_id.strip()]
    if not normalized_ids:
        raise ValueError("Select at least one failed recipient for follow-up handoff")

    recipients = await _list_execution_recipients(
        session,
        tenant_id=tenant_id,
        execution_id=execution_id,
        limit=None,
    )
    recipients_by_id = {recipient.id: recipient for recipient in recipients}
    results: list[MarketingExecutionFollowUpHandoffResult] = []

    for recipient_id in normalized_ids:
        recipient = recipients_by_id.get(recipient_id)
        if recipient is None:
            results.append(
                MarketingExecutionFollowUpHandoffResult(
                    recipient_id=recipient_id,
                    contact_name="Unknown recipient",
                    email="",
                    status="failed",
                    support_ticket_id=None,
                    message="Recipient does not exist in this execution scope.",
                )
            )
            continue

        if recipient.status != "failed":
            results.append(
                MarketingExecutionFollowUpHandoffResult(
                    recipient_id=recipient.id,
                    contact_name=recipient.contact_name,
                    email=recipient.email,
                    status="failed",
                    support_ticket_id=None,
                    message="Only failed recipients can be handed off for follow-up.",
                )
            )
            continue

        if recipient.handoff_status == "created" and recipient.support_ticket_id:
            results.append(
                MarketingExecutionFollowUpHandoffResult(
                    recipient_id=recipient.id,
                    contact_name=recipient.contact_name,
                    email=recipient.email,
                    status="failed",
                    support_ticket_id=recipient.support_ticket_id,
                    message="already_handed_off",
                )
            )
            continue

        try:
            ticket = await create_ticket(
                session,
                tenant_id=tenant_id,
                title=_build_failed_recipient_follow_up_ticket_title(
                    campaign_name=campaign.name,
                    recipient=recipient,
                ),
                description=_build_failed_recipient_follow_up_ticket_description(
                    campaign_name=campaign.name,
                    execution_id=execution.id,
                    recipient=recipient,
                ),
                status="open",
                priority=priority,
                source="manual",
                contact_id=recipient.contact_id,
            )
            await session.execute(
                text(
                    """
                    update public.marketing_campaign_execution_recipients
                    set support_ticket_id = cast(:support_ticket_id as varchar),
                        handoff_at = now(),
                        handoff_by_user_id = cast(:handoff_by_user_id as varchar),
                        handoff_status = 'created',
                        updated_at = now()
                    where tenant_id = cast(:tenant_id as varchar)
                      and execution_id = cast(:execution_id as varchar)
                      and id = cast(:recipient_id as varchar)
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "execution_id": execution.id,
                    "recipient_id": recipient.id,
                    "support_ticket_id": ticket.id,
                    "handoff_by_user_id": handoff_by_user_id,
                },
            )
            results.append(
                MarketingExecutionFollowUpHandoffResult(
                    recipient_id=recipient.id,
                    contact_name=recipient.contact_name,
                    email=recipient.email,
                    status="created",
                    support_ticket_id=ticket.id,
                    message=None,
                )
            )
        except ValueError as exc:
            await session.execute(
                text(
                    """
                    update public.marketing_campaign_execution_recipients
                    set handoff_at = now(),
                        handoff_by_user_id = cast(:handoff_by_user_id as varchar),
                        handoff_status = 'failed',
                        updated_at = now()
                    where tenant_id = cast(:tenant_id as varchar)
                      and execution_id = cast(:execution_id as varchar)
                      and id = cast(:recipient_id as varchar)
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "execution_id": execution.id,
                    "recipient_id": recipient.id,
                    "handoff_by_user_id": handoff_by_user_id,
                },
            )
            results.append(
                MarketingExecutionFollowUpHandoffResult(
                    recipient_id=recipient.id,
                    contact_name=recipient.contact_name,
                    email=recipient.email,
                    status="failed",
                    support_ticket_id=None,
                    message=str(exc),
                )
            )

    created_count = sum(1 for item in results if item.status == "created")
    failed_count = len(results) - created_count
    return MarketingExecutionFollowUpHandoffResponse(
        execution_id=execution.id,
        campaign_id=campaign_id,
        requested_count=len(normalized_ids),
        created_count=created_count,
        failed_count=failed_count,
        results=results,
    )


async def _update_campaign_delivery_state(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    status: str,
    blocked_reason: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            update public.marketing_campaigns
            set status = cast(:status as varchar),
                blocked_reason = :blocked_reason,
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:campaign_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "status": status,
            "blocked_reason": blocked_reason,
        },
    )


async def _create_campaign_execution(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    channel: str,
    status: str,
    total_recipients: int,
    batch_size: int,
    queued_batch_count: int,
    initiated_by_user_id: str | None,
    blocked_reason: str | None = None,
    metadata: dict[str, object] | None = None,
) -> MarketingCampaignExecutionDetails:
    execution_id = str(uuid.uuid4())
    result = await session.execute(
        text(
            """
            insert into public.marketing_campaign_executions (
                id,
                tenant_id,
                campaign_id,
                channel,
                status,
                initiated_by_user_id,
                total_recipients,
                processed_recipients,
                sent_recipients,
                failed_recipients,
                batch_size,
                queued_batch_count,
                blocked_reason,
                metadata,
                started_at
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:campaign_id as varchar),
                cast(:channel as varchar),
                cast(:status as varchar),
                cast(:initiated_by_user_id as varchar),
                :total_recipients,
                0,
                0,
                0,
                :batch_size,
                :queued_batch_count,
                :blocked_reason,
                cast(:metadata as jsonb),
                case when :status = 'sending' then now() else null end
            )
            returning
                id,
                tenant_id,
                campaign_id,
                channel,
                status,
                total_recipients,
                processed_recipients,
                sent_recipients,
                failed_recipients,
                batch_size,
                queued_batch_count,
                queue_job_id,
                blocked_reason,
                metadata,
                requested_at,
                started_at,
                completed_at,
                created_at,
                updated_at
            """
        ),
        {
            "id": execution_id,
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "channel": channel,
            "status": status,
            "initiated_by_user_id": initiated_by_user_id,
            "total_recipients": total_recipients,
            "batch_size": batch_size,
            "queued_batch_count": queued_batch_count,
            "blocked_reason": blocked_reason,
            "metadata": _dump_json(metadata or {}),
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create campaign execution")
    return _execution_from_row(row)


async def _update_campaign_execution_progress(
    session: AsyncSession,
    *,
    tenant_id: str,
    execution_id: str,
    status: str,
    processed_recipients: int,
    sent_recipients: int,
    failed_recipients: int,
    blocked_reason: str | None = None,
    mark_started: bool = False,
    mark_completed: bool = False,
) -> None:
    await session.execute(
        text(
            """
            update public.marketing_campaign_executions
            set status = cast(:status as varchar),
                processed_recipients = :processed_recipients,
                sent_recipients = :sent_recipients,
                failed_recipients = :failed_recipients,
                blocked_reason = :blocked_reason,
                started_at = case
                    when :mark_started then coalesce(started_at, now())
                    else started_at
                end,
                completed_at = case
                    when :mark_completed then now()
                    else completed_at
                end,
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:execution_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "status": status,
            "processed_recipients": processed_recipients,
            "sent_recipients": sent_recipients,
            "failed_recipients": failed_recipients,
            "blocked_reason": blocked_reason,
            "mark_started": mark_started,
            "mark_completed": mark_completed,
        },
    )


async def fail_marketing_campaign_execution(
    session: AsyncSession,
    *,
    execution_id: str,
    failure_reason: str,
) -> None:
    execution = await _get_campaign_execution_by_id(session, execution_id=execution_id)
    if execution is None:
        raise ValueError("Campaign execution does not exist")

    recipients = await _list_execution_recipients(
        session,
        tenant_id=execution.tenant_id,
        execution_id=execution.id,
        limit=None,
    )
    pending_recipient_count = sum(1 for recipient in recipients if recipient.status == "pending")

    if pending_recipient_count > 0:
        await session.execute(
            text(
                """
                update public.marketing_campaign_execution_recipients
                set status = 'failed',
                    failure_reason = cast(:failure_reason as text),
                    updated_at = now()
                where tenant_id = cast(:tenant_id as varchar)
                  and execution_id = cast(:execution_id as varchar)
                  and status = 'pending'
                """
            ),
            {
                "tenant_id": execution.tenant_id,
                "execution_id": execution.id,
                "failure_reason": failure_reason,
            },
        )

    sent_count = sum(1 for recipient in recipients if recipient.status == "sent")
    failed_count = (
        sum(1 for recipient in recipients if recipient.status in {"failed", "blocked"})
        + pending_recipient_count
    )
    processed_count = sent_count + failed_count

    await _update_campaign_execution_progress(
        session,
        tenant_id=execution.tenant_id,
        execution_id=execution.id,
        status="failed",
        processed_recipients=max(processed_count, execution.processed_recipients),
        sent_recipients=max(sent_count, execution.sent_recipients),
        failed_recipients=max(failed_count, execution.failed_recipients),
        blocked_reason=failure_reason,
        mark_started=False,
        mark_completed=True,
    )

    campaign = await get_marketing_campaign_by_id(
        session,
        tenant_id=execution.tenant_id,
        campaign_id=execution.campaign_id,
    )
    if campaign is not None:
        await _update_campaign_delivery_state(
            session,
            tenant_id=execution.tenant_id,
            campaign_id=execution.campaign_id,
            status="failed",
            blocked_reason=failure_reason,
        )


async def _insert_execution_recipients(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    execution_id: str,
    contacts: list[ContactDetails],
    batch_size: int,
) -> None:
    for index, contact in enumerate(contacts):
        email = _normalize_email(contact.email)
        if not email:
            continue
        await session.execute(
            text(
                """
                insert into public.marketing_campaign_execution_recipients (
                    id,
                    tenant_id,
                    execution_id,
                campaign_id,
                contact_id,
                email,
                phone,
                first_name,
                last_name,
                company,
                    batch_number,
                    status
                )
                values (
                    cast(:id as varchar),
                    cast(:tenant_id as varchar),
                    cast(:execution_id as varchar),
                    cast(:campaign_id as varchar),
                    cast(:contact_id as varchar),
                    cast(:email as varchar),
                    cast(:phone as varchar),
                    cast(:first_name as varchar),
                    cast(:last_name as varchar),
                    cast(:company as varchar),
                    :batch_number,
                    'pending'
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "execution_id": execution_id,
                "campaign_id": campaign_id,
                "contact_id": contact.id,
                "email": email,
                "phone": contact.phone,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "company": contact.company,
                "batch_number": (index // batch_size) + 1,
            },
        )


async def start_email_campaign_execution(
    session: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    initiated_by_user_id: str | None = None,
) -> MarketingCampaignDetail:
    campaign = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if campaign is None:
        raise ValueError("Campaign does not exist")

    queue_ready = True
    audience_summary = await _resolve_audience_summary(session, tenant_id=tenant_id, campaign=campaign)
    send_readiness = await _build_send_readiness(
        session,
        tenant_id=tenant_id,
        campaign=campaign,
        queue_ready=queue_ready,
        audience_summary=audience_summary,
    )

    if not send_readiness.can_send:
        raise ValueError("; ".join(send_readiness.blocked_reasons))

    preview_records = await _build_campaign_audience_preview_recipient_records(
        session,
        tenant_id=tenant_id,
        campaign=campaign,
    )
    preview_recipients = [record.preview for record in preview_records]
    eligible_contacts = [
        record.contact
        for record in preview_records
        if record.preview.eligibility_status == "eligible"
    ]

    if not eligible_contacts:
        raise ValueError("Email campaigns require at least one audience contact with an email address")

    latest_execution = await _get_latest_campaign_execution(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
    )
    if latest_execution and latest_execution.status == "sending":
        raise ValueError("Campaign execution is already in progress")
    if latest_execution and latest_execution.status == "completed":
        raise ValueError("Completed campaigns are protected from duplicate replay in this slice")

    exclusion_counts = _build_audience_preview_exclusion_counts(preview_recipients)
    snapshot = _build_execution_snapshot(
        audience_summary=audience_summary,
        total_matched_records=len(preview_recipients),
        eligible_recipients=len(eligible_contacts),
        exclusion_counts=exclusion_counts,
    )
    queued_batch_count = max(1, math.ceil(len(eligible_contacts) / EMAIL_CAMPAIGN_BATCH_SIZE))
    execution = await _create_campaign_execution(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        channel=campaign.channel,
        status="queued",
        total_recipients=len(eligible_contacts),
        batch_size=EMAIL_CAMPAIGN_BATCH_SIZE,
        queued_batch_count=queued_batch_count,
        initiated_by_user_id=initiated_by_user_id,
        metadata=_execution_snapshot_to_metadata(snapshot),
    )
    await _insert_execution_recipients(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        execution_id=execution.id,
        contacts=eligible_contacts,
        batch_size=EMAIL_CAMPAIGN_BATCH_SIZE,
    )

    job_id = enqueue_marketing_campaign_execution(execution_id=execution.id, tenant_id=tenant_id)
    if not job_id:
        await session.execute(
            text(
                """
                update public.marketing_campaign_executions
                set status = 'blocked',
                    blocked_reason = :blocked_reason,
                    completed_at = now(),
                    updated_at = now()
                where tenant_id = cast(:tenant_id as varchar)
                  and id = cast(:execution_id as varchar)
                """
            ),
            {
                "tenant_id": tenant_id,
                "execution_id": execution.id,
                "blocked_reason": "Background worker queue is unavailable, so bulk email dispatch is blocked.",
            },
        )
        await session.execute(
            text(
                """
                update public.marketing_campaign_execution_recipients
                set status = 'blocked',
                    failure_reason = :reason,
                    updated_at = now()
                where tenant_id = cast(:tenant_id as varchar)
                  and execution_id = cast(:execution_id as varchar)
                """
            ),
            {
                "tenant_id": tenant_id,
                "execution_id": execution.id,
                "reason": "Background worker queue is unavailable.",
            },
        )
        await _update_campaign_delivery_state(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            status="blocked",
            blocked_reason="Background worker queue is unavailable, so bulk email dispatch is blocked.",
        )
        return await get_marketing_campaign_detail(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            queue_ready=False,
        )

    await session.execute(
        text(
            """
            update public.marketing_campaign_executions
            set queue_job_id = cast(:queue_job_id as varchar),
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:execution_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "execution_id": execution.id, "queue_job_id": job_id},
    )
    await _update_campaign_delivery_state(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        status="sending",
        blocked_reason=None,
    )

    return await get_marketing_campaign_detail(
        session,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        queue_ready=True,
    )


async def process_email_campaign_execution(
    session: AsyncSession,
    *,
    execution_id: str,
) -> None:
    execution = await _get_campaign_execution_by_id(session, execution_id=execution_id)
    if execution is None:
        raise ValueError("Campaign execution does not exist")
    if execution.status in {"completed", "failed", "blocked"}:
        return

    campaign = await get_marketing_campaign_by_id(
        session,
        tenant_id=execution.tenant_id,
        campaign_id=execution.campaign_id,
    )
    if campaign is None:
        await fail_marketing_campaign_execution(
            session,
            execution_id=execution.id,
            failure_reason="Campaign no longer exists for this execution.",
        )
        return

    recipients = await _list_execution_recipients(
        session,
        tenant_id=execution.tenant_id,
        execution_id=execution.id,
        limit=None,
    )
    sent_count = sum(1 for recipient in recipients if recipient.status == "sent")
    failed_count = sum(1 for recipient in recipients if recipient.status in {"failed", "blocked"})
    processed_count = sent_count + failed_count
    pending_recipients = [recipient for recipient in recipients if recipient.status == "pending"]

    integrations = await get_marketing_integrations(session, tenant_id=execution.tenant_id)
    smtp_result = await session.execute(
        text(
            """
            select smtp_settings
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": execution.tenant_id},
    )
    smtp_payload = _load_json((smtp_result.mappings().first() or {}).get("smtp_settings"))
    smtp_password = smtp_payload.get("smtp_password")

    if not integrations.smtp.smtp_host or not integrations.smtp.from_email or not smtp_password:
        await fail_marketing_campaign_execution(
            session,
            execution_id=execution.id,
            failure_reason="SMTP must be configured and enabled before email campaigns can send.",
        )
        return

    await _update_campaign_execution_progress(
        session,
        tenant_id=execution.tenant_id,
        execution_id=execution.id,
        status="sending",
        processed_recipients=processed_count,
        sent_recipients=sent_count,
        failed_recipients=failed_count,
        blocked_reason=None,
        mark_started=True,
        mark_completed=False,
    )

    for recipient in pending_recipients:
        message = EmailMessage()
        message["From"] = integrations.smtp.from_email
        message["To"] = recipient.email
        message["Subject"] = campaign.subject or campaign.name
        message.set_content(campaign.message_body)

        try:
            await aiosmtplib.send(
                message,
                hostname=integrations.smtp.smtp_host,
                port=int(integrations.smtp.smtp_port),
                username=integrations.smtp.smtp_username,
                password=str(smtp_password),
                start_tls=bool(integrations.smtp.use_tls and not integrations.smtp.use_ssl),
                use_tls=bool(integrations.smtp.use_ssl),
                timeout=10,
            )
            await session.execute(
                text(
                    """
                    update public.marketing_campaign_execution_recipients
                    set status = 'sent',
                        sent_at = now(),
                        failure_reason = null,
                        updated_at = now()
                    where tenant_id = cast(:tenant_id as varchar)
                      and id = cast(:recipient_id as varchar)
                    """
                ),
                {"tenant_id": execution.tenant_id, "recipient_id": recipient.id},
            )
            sent_count += 1
        except Exception as exc:
            await session.execute(
                text(
                    """
                    update public.marketing_campaign_execution_recipients
                    set status = 'failed',
                        failure_reason = cast(:failure_reason as text),
                        updated_at = now()
                    where tenant_id = cast(:tenant_id as varchar)
                      and id = cast(:recipient_id as varchar)
                    """
                ),
                {
                    "tenant_id": execution.tenant_id,
                    "recipient_id": recipient.id,
                    "failure_reason": str(exc),
                },
            )
            failed_count += 1
        processed_count += 1
        await _update_campaign_execution_progress(
            session,
            tenant_id=execution.tenant_id,
            execution_id=execution.id,
            status="sending",
            processed_recipients=processed_count,
            sent_recipients=sent_count,
            failed_recipients=failed_count,
            blocked_reason=None,
            mark_started=False,
            mark_completed=False,
        )

    next_status = "completed" if failed_count == 0 else "failed"
    await _update_campaign_execution_progress(
        session,
        tenant_id=execution.tenant_id,
        execution_id=execution.id,
        status=next_status,
        processed_recipients=processed_count,
        sent_recipients=sent_count,
        failed_recipients=failed_count,
        blocked_reason=None if next_status == "completed" else "Some recipients failed during SMTP dispatch.",
        mark_started=False,
        mark_completed=True,
    )
    await _update_campaign_delivery_state(
        session,
        tenant_id=execution.tenant_id,
        campaign_id=execution.campaign_id,
        status=next_status,
        blocked_reason=None if next_status == "completed" else "Some recipients failed during SMTP dispatch.",
    )


def _split_name(full_name: str | None, fallback_email: str | None) -> tuple[str, str | None]:
    normalized_name = _clean_optional(full_name)
    if not normalized_name:
        fallback = _clean_optional(fallback_email) or "Imported contact"
        return fallback.split("@", 1)[0][:100], None
    parts = normalized_name.split()
    if len(parts) == 1:
        return parts[0][:100], None
    return parts[0][:100], " ".join(parts[1:])[:100]


def _parse_contact_import_rows(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(StringIO(csv_text))
    return [{str(key or "").strip(): str(value or "").strip() for key, value in row.items()} for row in reader]


async def preview_contact_import(
    session: AsyncSession,
    *,
    tenant_id: str,
    csv_text: str,
) -> ContactImportPreviewResult:
    rows = _parse_contact_import_rows(csv_text)
    preview_rows: list[ContactImportPreviewRow] = []
    seen_emails: set[str] = set()
    ready_rows = 0
    skipped_rows = 0
    error_rows = 0

    for index, row in enumerate(rows, start=1):
        full_name = _clean_optional(row.get("full_name") or row.get("name") or row.get("first_name"))
        email = _normalize_email(row.get("email"))
        phone = _clean_optional(row.get("phone"))
        company = _clean_optional(row.get("company"))

        if not full_name and not email:
            preview_rows.append(
                ContactImportPreviewRow(
                    row_number=index,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    company=company,
                    status="error",
                    message="Each row needs at least a name or email.",
                )
            )
            error_rows += 1
            continue

        if email and email in seen_emails:
            preview_rows.append(
                ContactImportPreviewRow(
                    row_number=index,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    company=company,
                    status="skipped",
                    message="Duplicate email appears more than once in this CSV.",
                )
            )
            skipped_rows += 1
            continue

        if email:
            seen_emails.add(email)
            if await _contact_email_exists(session, tenant_id=tenant_id, email=email):
                preview_rows.append(
                    ContactImportPreviewRow(
                        row_number=index,
                        full_name=full_name,
                        email=email,
                        phone=phone,
                        company=company,
                        status="skipped",
                        message="A contact with this email already exists for the tenant.",
                    )
                )
                skipped_rows += 1
                continue

        preview_rows.append(
            ContactImportPreviewRow(
                row_number=index,
                full_name=full_name,
                email=email,
                phone=phone,
                company=company,
                status="ready",
                message="Ready to import.",
            )
        )
        ready_rows += 1

    return ContactImportPreviewResult(
        total_rows=len(rows),
        ready_rows=ready_rows,
        skipped_rows=skipped_rows,
        error_rows=error_rows,
        rows=preview_rows,
    )


async def execute_contact_import(
    session: AsyncSession,
    *,
    tenant_id: str,
    csv_text: str,
) -> ContactImportPreviewResult:
    preview = await preview_contact_import(session, tenant_id=tenant_id, csv_text=csv_text)
    output_rows: list[ContactImportPreviewRow] = []
    imported_rows = 0
    skipped_rows = 0
    error_rows = 0
    parsed_rows = _parse_contact_import_rows(csv_text)

    for preview_row in preview.rows:
        if preview_row.status != "ready":
            output_rows.append(preview_row)
            if preview_row.status == "skipped":
                skipped_rows += 1
            else:
                error_rows += 1
            continue

        row = parsed_rows[preview_row.row_number - 1]
        full_name = _clean_optional(row.get("full_name") or row.get("name") or row.get("first_name"))
        email = _normalize_email(row.get("email"))
        phone = _clean_optional(row.get("phone"))
        company_name = _clean_optional(row.get("company"))
        job_title = _clean_optional(row.get("job_title"))
        notes = _clean_optional(row.get("notes") or row.get("source"))
        first_name, last_name = _split_name(full_name, email)
        company_id = None

        try:
            if company_name:
                company = await _find_company_by_name(session, tenant_id=tenant_id, company_name=company_name)
                if company is None:
                    company = await create_company(session, tenant_id=tenant_id, name=company_name)
                company_id = company.id

            await create_contact(
                session,
                tenant_id=tenant_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                company_id=company_id,
                company=company_name,
                job_title=job_title,
                notes=notes,
            )
            output_rows.append(
                ContactImportPreviewRow(
                    row_number=preview_row.row_number,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    company=company_name,
                    status="imported",
                    message="Imported successfully.",
                )
            )
            imported_rows += 1
        except Exception as exc:
            output_rows.append(
                ContactImportPreviewRow(
                    row_number=preview_row.row_number,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    company=company_name,
                    status="error",
                    message=str(exc),
                )
            )
            error_rows += 1

    return ContactImportPreviewResult(
        total_rows=preview.total_rows,
        ready_rows=imported_rows,
        skipped_rows=skipped_rows,
        error_rows=error_rows,
        rows=output_rows,
    )


async def export_contacts_csv(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> tuple[str, int]:
    rows = (
        await session.execute(
            text(
                """
                select
                    first_name,
                    last_name,
                    email,
                    phone,
                    company,
                    job_title,
                    notes
                from public.contacts
                where tenant_id = cast(:tenant_id as varchar)
                order by created_at desc, id desc
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["full_name", "email", "phone", "company", "job_title", "notes"])
    for row in rows:
        writer.writerow(
            [
                " ".join(part for part in [row["first_name"], row["last_name"]] if part).strip(),
                row["email"] or "",
                row["phone"] or "",
                row["company"] or "",
                row["job_title"] or "",
                row["notes"] or "",
            ]
        )
    return output.getvalue(), len(rows)


async def export_lead_contacts_csv(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> tuple[str, int]:
    rows = (
        await session.execute(
            text(
                """
                select distinct on (c.id, d.id)
                    c.first_name,
                    c.last_name,
                    c.email,
                    c.phone,
                    c.company,
                    d.name as deal_name,
                    d.stage,
                    d.status,
                    d.notes
                from public.deals d
                join public.contacts c
                  on c.id = d.contact_id
                 and c.tenant_id = d.tenant_id
                where d.tenant_id = cast(:tenant_id as varchar)
                order by c.id, d.id, d.updated_at desc
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["full_name", "email", "phone", "company", "deal_name", "stage", "status", "notes"])
    for row in rows:
        writer.writerow(
            [
                " ".join(part for part in [row["first_name"], row["last_name"]] if part).strip(),
                row["email"] or "",
                row["phone"] or "",
                row["company"] or "",
                row["deal_name"] or "",
                row["stage"] or "",
                row["status"] or "",
                row["notes"] or "",
            ]
        )
    return output.getvalue(), len(rows)


async def create_whatsapp_lead_intake(
    session: AsyncSession,
    *,
    tenant_id: str,
    sender_name: str | None,
    sender_phone: str,
    message_text: str,
    message_type: str | None,
    received_at: datetime | None,
    company_id: str | None,
    company_name: str | None,
    contact_id: str | None,
    email: str | None,
    amount: str | Decimal,
    currency: str,
    campaign_id: str | None,
    notes: str | None,
    whatsapp_account_id: str | None,
) -> WhatsAppLeadIntakeResult:
    integrations = await get_marketing_integrations(session, tenant_id=tenant_id)
    campaign = None
    if campaign_id is not None:
        campaign = await get_marketing_campaign_by_id(session, tenant_id=tenant_id, campaign_id=campaign_id)
        if campaign is None:
            raise ValueError("Campaign does not exist")

    normalized_payload = parse_inbound_whatsapp_lead(
        {
            "whatsapp_account_id": _clean_optional(whatsapp_account_id)
            or integrations.whatsapp.business_account_id
            or "manual-whatsapp-intake",
            "sender_phone": sender_phone,
            "sender_name": sender_name,
            "message_text": message_text,
            "message_type": message_type,
            "received_at": received_at.isoformat() if received_at is not None else None,
            "campaign": campaign.name if campaign is not None else None,
        },
        tenant_id=tenant_id,
    )

    resolved_contact = None
    if contact_id is not None:
        resolved_contact = await get_contact_by_id(session, tenant_id=tenant_id, contact_id=contact_id)
        if resolved_contact is None:
            raise ValueError("Contact does not exist")

    resolved_company = None
    normalized_company_id = _clean_optional(company_id)
    normalized_company_name = _clean_optional(company_name)
    if normalized_company_id is not None:
        resolved_company = await get_company_by_id(session, tenant_id=tenant_id, company_id=normalized_company_id)
        if resolved_company is None:
            raise ValueError("Company does not exist")
    elif resolved_contact is not None and resolved_contact.company_id is not None:
        resolved_company = await get_company_by_id(
            session,
            tenant_id=tenant_id,
            company_id=str(resolved_contact.company_id),
        )
    elif normalized_company_name is not None:
        resolved_company = await _find_company_by_name(
            session,
            tenant_id=tenant_id,
            company_name=normalized_company_name,
        )
        if resolved_company is None:
            try:
                resolved_company = await create_company(
                    session,
                    tenant_id=tenant_id,
                    name=normalized_company_name,
                    phone=normalized_payload.sender_phone,
                    notes="Created from manual WhatsApp lead intake.",
                )
            except IntegrityError as exc:
                _raise_for_whatsapp_intake_integrity_error(exc)

    if resolved_company is None:
        raise ValueError(
            "Select an existing company, choose a contact with a company, or enter a new company name."
        )

    if resolved_contact is not None and resolved_contact.company_id != resolved_company.id:
        raise ValueError("Contact does not belong to the selected company")

    if resolved_contact is None:
        resolved_contact = await _find_contact_by_phone_or_email(
            session,
            tenant_id=tenant_id,
            company_id=resolved_company.id,
            phone=normalized_payload.sender_phone,
            email=_clean_optional(email),
        )

    if resolved_contact is None:
        contact_defaults = build_new_lead_contact_defaults(normalized_payload)
        contact_notes_parts = [contact_defaults.get("notes")] if contact_defaults.get("notes") else []
        normalized_email = _clean_optional(email)
        extra_notes = _clean_optional(notes)
        if normalized_email:
            contact_notes_parts.append(f"Email: {normalized_email}")
        if extra_notes:
            contact_notes_parts.append(extra_notes)
        try:
            resolved_contact = await create_contact(
                session,
                tenant_id=tenant_id,
                first_name=str(contact_defaults["first_name"]),
                last_name=contact_defaults["last_name"],
                email=normalized_email,
                phone=normalized_payload.sender_phone,
                company_id=resolved_company.id,
                company=resolved_company.name,
                job_title=contact_defaults["job_title"],
                notes="\n".join(part for part in contact_notes_parts if part),
            )
        except IntegrityError as exc:
            _raise_for_whatsapp_intake_integrity_error(exc)

    deal_defaults = build_new_lead_deal_defaults(
        normalized_payload,
        company_id=resolved_company.id,
    )
    normalized_amount = _normalize_money_amount(amount)
    normalized_currency = _normalize_currency(currency)
    deal_notes_parts = [deal_defaults["notes"]]
    normalized_email = _clean_optional(email)
    extra_notes = _clean_optional(notes)
    if normalized_email:
        deal_notes_parts.append(f"Lead email: {normalized_email}")
    if extra_notes:
        deal_notes_parts.append(extra_notes)

    try:
        deal = await create_deal(
            session,
            tenant_id=tenant_id,
            name=str(deal_defaults["name"]),
            company_id=resolved_company.id,
            contact_id=resolved_contact.id,
            product_id=None,
            amount=normalized_amount,
            currency=normalized_currency,
            stage=str(deal_defaults["stage"]),
            status=str(deal_defaults["status"]),
            expected_close_date=None,
            notes="\n".join(part for part in deal_notes_parts if part),
        )
    except IntegrityError as exc:
        _raise_for_whatsapp_intake_integrity_error(exc)

    return WhatsAppLeadIntakeResult(
        deal=MarketingRecordReference(id=deal.id, label=deal.name),
        company=MarketingRecordReference(id=resolved_company.id, label=resolved_company.name),
        contact=MarketingRecordReference(
            id=resolved_contact.id,
            label=" ".join(
                [value for value in [resolved_contact.first_name, resolved_contact.last_name] if value]
            ).strip()
            or resolved_contact.email
            or resolved_contact.phone
            or resolved_contact.id,
        ),
        campaign=MarketingRecordReference(id=campaign.id, label=campaign.name) if campaign else None,
    )

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field
from app.support.schemas import SupportTicketPriority


class WhatsAppIntegrationSettingsUpdateRequest(BaseModel):
    business_account_id: str | None = Field(default=None, max_length=128)
    phone_number_id: str | None = Field(default=None, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)
    access_token: str | None = Field(default=None, max_length=512)
    webhook_verify_token: str | None = Field(default=None, max_length=512)
    is_enabled: bool = True


class WhatsAppIntegrationSettingsOut(BaseModel):
    business_account_id: str | None = None
    phone_number_id: str | None = None
    display_name: str | None = None
    access_token_set: bool = False
    webhook_verify_token_set: bool = False
    is_enabled: bool = False
    updated_at: datetime | None = None


class SmtpSettingsUpdateRequest(BaseModel):
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = Field(default=None, max_length=255)
    smtp_password: str | None = Field(default=None, max_length=512)
    from_email: EmailStr | None = None
    from_name: str | None = Field(default=None, max_length=255)
    use_tls: bool = True
    use_ssl: bool = False
    is_enabled: bool = True


class SmtpSettingsOut(BaseModel):
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    from_email: EmailStr | None = None
    from_name: str | None = None
    use_tls: bool = True
    use_ssl: bool = False
    password_set: bool = False
    is_enabled: bool = False
    updated_at: datetime | None = None


class MarketingIntegrationsOut(BaseModel):
    whatsapp: WhatsAppIntegrationSettingsOut
    smtp: SmtpSettingsOut
    social: list["SocialIntegrationProviderOut"] = Field(default_factory=list)


class SmtpConnectionTestResponse(BaseModel):
    success: bool
    message: str


MarketingCampaignChannel = Literal["email", "whatsapp"]
MarketingCampaignAudienceType = Literal["all_contacts", "target_company_contacts", "target_contact_only"]
MarketingCampaignEditableStatus = Literal["draft", "scheduled"]
MarketingCampaignStatus = Literal["draft", "scheduled", "sending", "completed", "failed", "blocked"]
MarketingExecutionStatus = Literal["queued", "sending", "completed", "failed", "blocked"]
MarketingExecutionRecipientStatus = Literal["pending", "sent", "failed", "blocked"]
MarketingExecutionRecipientFilter = Literal["all", "failed", "sent", "pending", "blocked"]
MarketingSocialConfigurationState = Literal["not_configured", "incomplete", "configured"]
MarketingImportRowStatus = Literal["ready", "skipped", "error", "imported"]
MarketingAudienceRecipientEligibilityStatus = Literal[
    "eligible",
    "missing_email",
    "missing_phone",
    "excluded_by_target_context",
    "duplicate_contact_method",
    "blocked_by_campaign_rules",
]


class MarketingCampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel: MarketingCampaignChannel
    audience_type: MarketingCampaignAudienceType = "all_contacts"
    audience_description: str | None = None
    target_company_id: str | None = Field(default=None, min_length=1, max_length=36)
    target_contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    subject: str | None = Field(default=None, max_length=255)
    message_body: str = Field(..., min_length=1)
    status: MarketingCampaignEditableStatus = "draft"
    scheduled_for: datetime | None = None


class MarketingCampaignUpdateRequest(MarketingCampaignCreateRequest):
    pass


class MarketingCampaignOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    channel: MarketingCampaignChannel
    audience_type: MarketingCampaignAudienceType
    audience_description: str | None = None
    target_company_id: str | None = None
    target_contact_id: str | None = None
    subject: str | None = None
    message_body: str
    status: MarketingCampaignStatus
    scheduled_for: datetime | None = None
    blocked_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class MarketingCampaignListResponse(BaseModel):
    items: list[MarketingCampaignOut]
    total: int


class MarketingAudienceSummaryOut(BaseModel):
    audience_type: MarketingCampaignAudienceType
    summary_label: str
    target_company_label: str | None = None
    target_contact_label: str | None = None
    total_contacts: int
    email_eligible_contacts: int
    blocked_reasons: list[str] = Field(default_factory=list)


class MarketingSendReadinessOut(BaseModel):
    channel: MarketingCampaignChannel
    can_send: bool
    smtp_ready: bool
    queue_ready: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    capacity_note: str


class MarketingCampaignExecutionOut(BaseModel):
    id: str
    tenant_id: str
    campaign_id: str
    channel: MarketingCampaignChannel
    status: MarketingExecutionStatus
    total_recipients: int
    processed_recipients: int
    sent_recipients: int
    failed_recipients: int
    batch_size: int
    queued_batch_count: int
    queue_job_id: str | None = None
    blocked_reason: str | None = None
    requested_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MarketingCampaignExecutionSnapshotOut(BaseModel):
    audience_type: MarketingCampaignAudienceType
    summary_label: str
    target_company_label: str | None = None
    target_contact_label: str | None = None
    total_matched_records: int
    eligible_recipients: int
    excluded_recipients: int
    exclusion_counts: list["MarketingAudiencePreviewExclusionCountOut"] = Field(default_factory=list)


class MarketingCampaignExecutionRecipientOut(BaseModel):
    id: str
    execution_id: str
    campaign_id: str
    contact_id: str | None = None
    contact_name: str
    email: str
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    batch_number: int
    status: MarketingExecutionRecipientStatus
    failure_reason: str | None = None
    support_ticket_id: str | None = None
    handoff_at: datetime | None = None
    handoff_by_user_id: str | None = None
    handoff_status: Literal["created", "failed"] | None = None
    sent_at: datetime | None = None


class MarketingCampaignExecutionRecipientStatusCountOut(BaseModel):
    status: MarketingExecutionRecipientFilter
    count: int


class MarketingExecutionFollowUpHandoffRequest(BaseModel):
    recipient_ids: list[str] = Field(default_factory=list)
    priority: SupportTicketPriority = "high"


class MarketingExecutionFollowUpHandoffResultStatusOut(BaseModel):
    recipient_id: str
    contact_name: str
    email: str
    status: Literal["created", "failed"]
    support_ticket_id: str | None = None
    message: str | None = None


class MarketingExecutionFollowUpHandoffResponseOut(BaseModel):
    execution_id: str
    campaign_id: str
    requested_count: int
    created_count: int
    failed_count: int
    results: list[MarketingExecutionFollowUpHandoffResultStatusOut] = Field(default_factory=list)


class MarketingCampaignExecutionDetailOut(BaseModel):
    execution: MarketingCampaignExecutionOut
    execution_snapshot: MarketingCampaignExecutionSnapshotOut | None = None
    recipient_filter: MarketingExecutionRecipientFilter
    recipient_counts: list[MarketingCampaignExecutionRecipientStatusCountOut] = Field(default_factory=list)
    recipients: list[MarketingCampaignExecutionRecipientOut] = Field(default_factory=list)


class MarketingCampaignExecutionListResponse(BaseModel):
    items: list[MarketingCampaignExecutionOut] = Field(default_factory=list)


class MarketingCampaignDetailOut(BaseModel):
    campaign: MarketingCampaignOut
    audience_summary: MarketingAudienceSummaryOut
    send_readiness: MarketingSendReadinessOut
    latest_execution: MarketingCampaignExecutionOut | None = None
    latest_execution_snapshot: MarketingCampaignExecutionSnapshotOut | None = None
    execution_history: list[MarketingCampaignExecutionOut] = Field(default_factory=list)
    recent_recipients: list[MarketingCampaignExecutionRecipientOut] = Field(default_factory=list)


class MarketingAudiencePreviewExclusionCountOut(BaseModel):
    reason: MarketingAudienceRecipientEligibilityStatus
    count: int


class MarketingAudiencePreviewRecipientOut(BaseModel):
    contact_id: str
    contact_name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    eligibility_status: MarketingAudienceRecipientEligibilityStatus
    exclusion_reason: str | None = None


class MarketingCampaignAudiencePreviewOut(BaseModel):
    campaign: MarketingCampaignOut
    audience_summary: MarketingAudienceSummaryOut
    send_readiness: MarketingSendReadinessOut
    total_matched_records: int
    eligible_recipients: int
    excluded_recipients: int
    exclusion_counts: list[MarketingAudiencePreviewExclusionCountOut] = Field(default_factory=list)
    sample_limit: int
    has_more_recipients: bool = False
    recipients: list[MarketingAudiencePreviewRecipientOut] = Field(default_factory=list)


class MarketingRecordReferenceOut(BaseModel):
    id: str
    label: str


class WhatsAppLeadIntakeRequest(BaseModel):
    sender_name: str | None = Field(default=None, max_length=255)
    sender_phone: str = Field(..., min_length=3, max_length=50)
    message_text: str = Field(..., min_length=1)
    message_type: str | None = Field(default="text", max_length=32)
    received_at: datetime | None = None
    company_id: str | None = Field(default=None, min_length=1, max_length=36)
    company_name: str | None = Field(default=None, max_length=255)
    contact_id: str | None = Field(default=None, min_length=1, max_length=36)
    email: EmailStr | None = None
    amount: str = Field(default="0", min_length=1, max_length=32)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    campaign_id: str | None = Field(default=None, min_length=1, max_length=36)
    notes: str | None = None
    whatsapp_account_id: str | None = Field(default=None, max_length=128)


class WhatsAppLeadIntakeOut(BaseModel):
    deal: MarketingRecordReferenceOut
    company: MarketingRecordReferenceOut
    contact: MarketingRecordReferenceOut | None = None
    campaign: MarketingRecordReferenceOut | None = None


class SocialIntegrationProviderUpdateRequest(BaseModel):
    account_id: str | None = Field(default=None, max_length=255)
    account_name: str | None = Field(default=None, max_length=255)
    page_id: str | None = Field(default=None, max_length=255)
    profile_id: str | None = Field(default=None, max_length=255)
    access_token: str | None = Field(default=None, max_length=512)
    refresh_token: str | None = Field(default=None, max_length=512)
    webhook_secret: str | None = Field(default=None, max_length=512)
    is_enabled: bool = False


class SocialIntegrationProviderOut(BaseModel):
    provider: Literal["facebook", "instagram", "tiktok", "linkedin", "x"]
    display_name: str
    account_id: str | None = None
    account_name: str | None = None
    page_id: str | None = None
    profile_id: str | None = None
    access_token_set: bool
    refresh_token_set: bool
    webhook_secret_set: bool
    is_enabled: bool
    configuration_state: MarketingSocialConfigurationState
    validation_errors: list[str] = Field(default_factory=list)
    operator_summary: str
    updated_at: datetime | None = None


class ContactImportPreviewRequest(BaseModel):
    csv_text: str = Field(..., min_length=1)
    duplicate_strategy: Literal["skip"] = "skip"


class ContactImportPreviewRowOut(BaseModel):
    row_number: int
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    status: MarketingImportRowStatus
    message: str


class ContactImportPreviewOut(BaseModel):
    total_rows: int
    ready_rows: int
    skipped_rows: int
    error_rows: int
    rows: list[ContactImportPreviewRowOut]


class ContactImportExecuteOut(BaseModel):
    total_rows: int
    imported_rows: int
    skipped_rows: int
    error_rows: int
    rows: list[ContactImportPreviewRowOut]


class ContactExportOptionsOut(BaseModel):
    filename: str
    row_count: int

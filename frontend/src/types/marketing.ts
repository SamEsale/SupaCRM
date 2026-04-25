export type MarketingCampaignChannel = "email" | "whatsapp";
export type MarketingCampaignAudienceType =
    | "all_contacts"
    | "target_company_contacts"
    | "target_contact_only";
export type MarketingCampaignEditableStatus = "draft" | "scheduled";
export type MarketingCampaignStatus =
    | MarketingCampaignEditableStatus
    | "sending"
    | "completed"
    | "failed"
    | "blocked";
export type MarketingCampaignExecutionStatus =
    | "queued"
    | "sending"
    | "completed"
    | "failed"
    | "blocked";
export type MarketingExecutionRecipientResultFilter =
    | "all"
    | "failed"
    | "sent"
    | "pending"
    | "blocked";
export type MarketingAudienceRecipientEligibilityStatus =
    | "eligible"
    | "missing_email"
    | "missing_phone"
    | "excluded_by_target_context"
    | "duplicate_contact_method"
    | "blocked_by_campaign_rules";

export interface MarketingCampaign {
    id: string;
    tenant_id: string;
    name: string;
    channel: MarketingCampaignChannel;
    audience_type: MarketingCampaignAudienceType;
    audience_description: string | null;
    target_company_id: string | null;
    target_contact_id: string | null;
    subject: string | null;
    message_body: string;
    status: MarketingCampaignStatus;
    scheduled_for: string | null;
    created_at: string;
    updated_at: string;
}

export interface MarketingCampaignListResponse {
    items: MarketingCampaign[];
    total: number;
}

export interface MarketingCampaignUpsertRequest {
    name: string;
    channel: MarketingCampaignChannel;
    audience_type: MarketingCampaignAudienceType;
    audience_description: string | null;
    target_company_id: string | null;
    target_contact_id: string | null;
    subject: string | null;
    message_body: string;
    status: MarketingCampaignEditableStatus;
    scheduled_for: string | null;
}

export interface MarketingAudienceSummary {
    audience_type: MarketingCampaignAudienceType;
    summary_label: string;
    target_company_label: string | null;
    target_contact_label: string | null;
    total_contacts: number;
    email_eligible_contacts: number;
    blocked_reasons: string[];
}

export interface MarketingSendReadiness {
    channel: MarketingCampaignChannel;
    can_send: boolean;
    smtp_ready: boolean;
    queue_ready: boolean;
    blocked_reasons: string[];
    capacity_note: string;
}

export interface MarketingAudiencePreviewExclusionCount {
    reason: MarketingAudienceRecipientEligibilityStatus;
    count: number;
}

export interface MarketingAudiencePreviewRecipient {
    contact_id: string;
    contact_name: string;
    email: string | null;
    phone: string | null;
    company: string | null;
    eligibility_status: MarketingAudienceRecipientEligibilityStatus;
    exclusion_reason: string | null;
}

export interface MarketingCampaignAudiencePreview {
    campaign: MarketingCampaign;
    audience_summary: MarketingAudienceSummary;
    send_readiness: MarketingSendReadiness;
    total_matched_records: number;
    eligible_recipients: number;
    excluded_recipients: number;
    exclusion_counts: MarketingAudiencePreviewExclusionCount[];
    sample_limit: number;
    has_more_recipients: boolean;
    recipients: MarketingAudiencePreviewRecipient[];
}

export interface MarketingCampaignExecutionSnapshot {
    audience_type: MarketingCampaignAudienceType;
    summary_label: string;
    target_company_label: string | null;
    target_contact_label: string | null;
    total_matched_records: number;
    eligible_recipients: number;
    excluded_recipients: number;
    exclusion_counts: MarketingAudiencePreviewExclusionCount[];
}

export interface MarketingCampaignExecution {
    id: string;
    tenant_id: string;
    campaign_id: string;
    channel: MarketingCampaignChannel;
    status: MarketingCampaignExecutionStatus;
    total_recipients: number;
    processed_recipients: number;
    sent_recipients: number;
    failed_recipients: number;
    batch_size: number;
    queued_batch_count: number;
    queue_job_id: string | null;
    blocked_reason: string | null;
    requested_at: string;
    started_at: string | null;
    completed_at: string | null;
    created_at: string;
    updated_at: string;
}

export interface MarketingCampaignExecutionRecipient {
    id: string;
    execution_id: string;
    campaign_id: string;
    contact_id: string | null;
    contact_name: string;
    email: string;
    phone: string | null;
    first_name: string | null;
    last_name: string | null;
    company: string | null;
    batch_number: number;
    status: "pending" | "sent" | "failed" | "blocked";
    failure_reason: string | null;
    support_ticket_id: string | null;
    handoff_at: string | null;
    handoff_by_user_id: string | null;
    handoff_status: "created" | "failed" | null;
    sent_at: string | null;
}

export interface MarketingCampaignDetail {
    campaign: MarketingCampaign;
    audience_summary: MarketingAudienceSummary;
    send_readiness: MarketingSendReadiness;
    latest_execution: MarketingCampaignExecution | null;
    latest_execution_snapshot: MarketingCampaignExecutionSnapshot | null;
    execution_history: MarketingCampaignExecution[];
    recent_recipients: MarketingCampaignExecutionRecipient[];
}

export interface MarketingCampaignExecutionRecipientStatusCount {
    status: MarketingExecutionRecipientResultFilter;
    count: number;
}

export interface MarketingCampaignExecutionDetail {
    execution: MarketingCampaignExecution;
    execution_snapshot: MarketingCampaignExecutionSnapshot | null;
    recipient_filter: MarketingExecutionRecipientResultFilter;
    recipient_counts: MarketingCampaignExecutionRecipientStatusCount[];
    recipients: MarketingCampaignExecutionRecipient[];
}

export interface MarketingExecutionFollowUpHandoffRequest {
    recipient_ids: string[];
    priority: "low" | "medium" | "high" | "urgent";
}

export interface MarketingExecutionFollowUpHandoffResult {
    recipient_id: string;
    contact_name: string;
    email: string;
    status: "created" | "failed";
    support_ticket_id: string | null;
    message: string | null;
}

export interface MarketingExecutionFollowUpHandoffResponse {
    execution_id: string;
    campaign_id: string;
    requested_count: number;
    created_count: number;
    failed_count: number;
    results: MarketingExecutionFollowUpHandoffResult[];
}

export interface MarketingRecordReference {
    id: string;
    label: string;
}

export interface WhatsAppLeadIntakeRequest {
    sender_name: string | null;
    sender_phone: string;
    message_text: string;
    message_type: string | null;
    received_at: string | null;
    company_id: string | null;
    company_name: string | null;
    contact_id: string | null;
    email: string | null;
    amount: string;
    currency: string;
    campaign_id: string | null;
    notes: string | null;
    whatsapp_account_id: string | null;
}

export interface WhatsAppLeadIntakeResponse {
    deal: MarketingRecordReference;
    company: MarketingRecordReference;
    contact: MarketingRecordReference | null;
    campaign: MarketingRecordReference | null;
}

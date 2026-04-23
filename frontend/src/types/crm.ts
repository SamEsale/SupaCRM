export interface Contact {
    id: string;
    tenant_id: string;
    first_name: string;
    last_name: string | null;
    email: string | null;
    phone: string | null;
    company_id: string | null;
    company: string | null;
    job_title: string | null;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface ContactsListResponse {
    items: Contact[];
    total: number;
}

export interface ContactImportRequest {
    csv_text: string;
    create_missing_companies: boolean;
}

export interface ContactImportRow {
    row_number: number;
    first_name: string | null;
    last_name: string | null;
    email: string | null;
    company: string | null;
    status: "imported" | "error";
    message: string;
}

export interface ContactImportResult {
    total_rows: number;
    imported_rows: number;
    error_rows: number;
    rows: ContactImportRow[];
}

export interface ContactCreateRequest {
    first_name: string;
    last_name: string | null;
    email: string | null;
    phone: string | null;
    company_id: string | null;
    company: string | null;
    job_title: string | null;
    notes: string | null;
}

export interface ContactUpdateRequest {
    first_name?: string | null;
    last_name?: string | null;
    email?: string | null;
    phone?: string | null;
    company_id?: string | null;
    company?: string | null;
    job_title?: string | null;
    notes?: string | null;
}

export interface Company {
    id: string;
    tenant_id: string;
    name: string;
    website: string | null;
    email: string | null;
    phone: string | null;
    industry: string | null;
    address: string | null;
    vat_number: string | null;
    registration_number: string | null;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface CompaniesListResponse {
    items: Company[];
    total: number;
}

export interface CompanyCreateRequest {
    name: string;
    website: string | null;
    email: string | null;
    phone: string | null;
    industry: string | null;
    address: string | null;
    vat_number: string | null;
    registration_number: string | null;
    notes: string | null;
}

export interface CompanyUpdateRequest {
    name?: string | null;
    website?: string | null;
    email?: string | null;
    phone?: string | null;
    industry?: string | null;
    address?: string | null;
    vat_number?: string | null;
    registration_number?: string | null;
    notes?: string | null;
}

export type DealStage =
    | "new lead"
    | "qualified lead"
    | "proposal sent"
    | "estimate sent"
    | "negotiating contract terms"
    | "contract signed"
    | "deal not secured";

export type DealStatus =
    | "open"
    | "in progress"
    | "won"
    | "lost";

export type LeadSource =
    | "manual"
    | "website"
    | "email"
    | "phone"
    | "referral"
    | "whatsapp"
    | "other";

export type DealListView =
    | "all"
    | "opportunities";

export interface Deal {
    id: string;
    tenant_id: string;
    name: string;
    company_id: string;
    contact_id: string | null;
    product_id: string | null;
    amount: string;
    currency: string;
    stage: DealStage;
    status: DealStatus;
    expected_close_date: string | null;
    notes: string | null;
    next_follow_up_at: string | null;
    follow_up_note: string | null;
    closed_at: string | null;
    created_at: string;
    updated_at: string;
}

export interface DealsListResponse {
    items: Deal[];
    total: number;
}

export interface DealCreateRequest {
    name: string;
    company_id: string;
    contact_id: string | null;
    product_id: string | null;
    amount: string;
    currency: string;
    stage: DealStage;
    status: DealStatus;
    expected_close_date: string | null;
    notes: string | null;
}

export interface DealUpdateRequest {
    name?: string | null;
    company_id?: string | null;
    contact_id?: string | null;
    product_id?: string | null;
    amount?: string | null;
    currency?: string | null;
    stage?: DealStage | null;
    status?: DealStatus | null;
    expected_close_date?: string | null;
    notes?: string | null;
}

export interface DealFollowUpUpdateRequest {
    next_follow_up_at: string | null;
    follow_up_note: string | null;
}

export interface LeadCreateRequest {
    name: string;
    company_id: string;
    contact_id: string | null;
    email: string | null;
    phone: string | null;
    amount: string;
    currency: string;
    source: LeadSource | null;
    notes: string | null;
}

export interface LeadImportRequest {
    csv_text: string;
    create_missing_companies: boolean;
}

export interface LeadImportRow {
    row_number: number;
    name: string | null;
    company: string | null;
    email: string | null;
    stage: string | null;
    status: string | null;
    result: "imported" | "error";
    message: string;
}

export interface LeadImportResult {
    total_rows: number;
    imported_rows: number;
    error_rows: number;
    rows: LeadImportRow[];
}

export interface PipelineStageCount {
    stage: DealStage;
    count: number;
}

export interface PipelineReportResponse {
    items: PipelineStageCount[];
    total: number;
}

export interface SalesStageSummary {
    stage: DealStage;
    count: number;
    open_amount: string;
    weighted_amount: string;
}

export interface SalesForecastSummary {
    total_open_pipeline_amount: string;
    weighted_pipeline_amount: string;
    won_amount: string;
    lost_amount: string;
    deals_won_this_period_count: number;
    deals_won_this_period_amount: string;
    deals_lost_this_period_count: number;
    deals_lost_this_period_amount: string;
    overdue_follow_up_count: number;
    due_today_follow_up_count: number;
    upcoming_follow_up_count: number;
    currencies: string[];
    report_period_start: string;
    report_period_end: string;
    generated_at: string;
}

export interface SalesForecastReportResponse {
    summary: SalesForecastSummary;
    stage_breakdown: SalesStageSummary[];
    opportunity_stage_breakdown: SalesStageSummary[];
}

export interface DeleteResponse {
    success: boolean;
    message: string;
}

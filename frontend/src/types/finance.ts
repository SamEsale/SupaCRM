export type InvoiceStatus =
    | "draft"
    | "issued"
    | "paid"
    | "overdue"
    | "cancelled";

export interface Invoice {
    id: string;
    tenant_id: string;
    number: string;
    company_id: string;
    contact_id: string | null;
    product_id: string | null;
    source_quote_id: string | null;
    issue_date: string;
    due_date: string;
    currency: string;
    total_amount: string;
    status: InvoiceStatus;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface RevenueStatusBreakdown {
    status: string;
    count: number;
    total_amount: string;
    currencies: string[];
}

export interface RevenueFlowSummary {
    quote_count: number;
    quote_created_this_period_count: number;
    invoice_count: number;
    invoice_created_this_period_count: number;
    invoice_issued_count: number;
    invoice_paid_count: number;
    invoice_overdue_count: number;
    quote_currencies: string[];
    invoice_currencies: string[];
    generated_at: string;
    report_period_start: string;
    report_period_end: string;
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

export interface RevenueFlowReport {
    sales_summary: SalesForecastSummary;
    summary: RevenueFlowSummary;
    quote_status_breakdown: RevenueStatusBreakdown[];
    invoice_status_breakdown: RevenueStatusBreakdown[];
}

export interface InvoicesListResponse {
    items: Invoice[];
    total: number;
}

export interface InvoiceCreateRequest {
    company_id: string;
    contact_id: string | null;
    product_id: string | null;
    source_quote_id?: string | null;
    issue_date: string;
    due_date: string;
    currency: string;
    total_amount: number;
    notes: string | null;
}

export interface InvoiceUpdateRequest {
    company_id?: string | null;
    contact_id?: string | null;
    product_id?: string | null;
    issue_date?: string | null;
    due_date?: string | null;
    currency?: string | null;
    total_amount?: number | null;
    notes?: string | null;
}

export interface InvoiceDeleteResponse {
    success: boolean;
    message: string;
}

export type QuoteStatus =
    | "draft"
    | "sent"
    | "accepted"
    | "rejected"
    | "expired";

export interface Quote {
    id: string;
    tenant_id: string;
    number: string;
    company_id: string;
    contact_id: string | null;
    deal_id: string | null;
    source_deal_id: string | null;
    product_id: string | null;
    issue_date: string;
    expiry_date: string;
    currency: string;
    total_amount: string;
    status: QuoteStatus;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface QuotesListResponse {
    items: Quote[];
    total: number;
}

export interface QuoteCreateRequest {
    company_id: string;
    contact_id: string | null;
    deal_id: string | null;
    source_deal_id?: string | null;
    product_id: string | null;
    issue_date: string;
    expiry_date: string;
    currency: string;
    total_amount: number;
    status: QuoteStatus;
    notes: string | null;
}

export interface QuoteUpdateRequest {
    company_id?: string | null;
    contact_id?: string | null;
    deal_id?: string | null;
    product_id?: string | null;
    issue_date?: string | null;
    expiry_date?: string | null;
    currency?: string | null;
    total_amount?: number | null;
    notes?: string | null;
}

export interface QuoteDeleteResponse {
    success: boolean;
    message: string;
}

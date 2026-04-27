export interface ReportPeriod {
    report_period_start: string;
    report_period_end: string;
    generated_at: string;
}

export interface ContactReportsSummary extends ReportPeriod {
    total_contacts: number;
    contacts_created_this_period_count: number;
    contacts_with_open_deals_count: number;
    contacts_with_won_deals_count: number;
    contacts_without_company_count: number;
    contacts_with_support_tickets_count: number;
}

export interface ContactCompanyBreakdown {
    company_id: string | null;
    company_name: string;
    contact_count: number;
}

export interface ContactReportItem {
    contact_id: string;
    full_name: string;
    company_id: string | null;
    company_name: string | null;
    email: string | null;
    phone: string | null;
    updated_at: string;
    open_deals_count: number;
    won_deals_count: number;
    support_ticket_count: number;
}

export interface ContactReportsSnapshot {
    summary: ContactReportsSummary;
    contacts_by_company: ContactCompanyBreakdown[];
    recent_contacts: ContactReportItem[];
}

export interface CompanyReportsSummary extends ReportPeriod {
    total_companies: number;
    companies_created_this_period_count: number;
    companies_with_open_deals_count: number;
    companies_with_won_deals_count: number;
    companies_with_contacts_count: number;
    companies_without_contacts_count: number;
    companies_with_invoices_count: number;
    companies_with_support_tickets_count: number;
}

export interface CompanyContactBreakdown {
    company_id: string;
    company_name: string;
    contact_count: number;
}

export interface CompanyReportItem {
    company_id: string;
    company_name: string;
    updated_at: string;
    contact_count: number;
    open_deals_count: number;
    won_deals_count: number;
    invoice_count: number;
    support_ticket_count: number;
}

export interface CompanyReportsSnapshot {
    summary: CompanyReportsSummary;
    contact_breakdown: CompanyContactBreakdown[];
    recent_companies: CompanyReportItem[];
}

export interface SupportReportsSummary extends ReportPeriod {
    total_tickets: number;
    open_tickets: number;
    in_progress_tickets: number;
    waiting_on_customer_tickets: number;
    resolved_tickets: number;
    closed_tickets: number;
    urgent_active_tickets: number;
    tickets_linked_to_deals_count: number;
    tickets_linked_to_invoices_count: number;
}

export interface SupportCountBreakdown {
    label: string;
    count: number;
}

export interface SupportCompanyBreakdown {
    company_id: string | null;
    company_name: string;
    ticket_count: number;
}

export interface SupportReportItem {
    ticket_id: string;
    title: string;
    status: string;
    priority: string;
    source: string;
    company_id: string | null;
    company_name: string | null;
    contact_id: string | null;
    related_deal_id: string | null;
    related_invoice_id: string | null;
    updated_at: string;
}

export interface SupportReportsSnapshot {
    summary: SupportReportsSummary;
    tickets_by_priority: SupportCountBreakdown[];
    tickets_by_source: SupportCountBreakdown[];
    tickets_by_company: SupportCompanyBreakdown[];
    recent_tickets: SupportReportItem[];
}

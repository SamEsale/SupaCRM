export type SupportTicketStatus =
    | "open"
    | "in progress"
    | "waiting on customer"
    | "resolved"
    | "closed";

export type SupportTicketPriority =
    | "low"
    | "medium"
    | "high"
    | "urgent";

export type SupportTicketSource =
    | "manual"
    | "email"
    | "whatsapp"
    | "phone"
    | "web";

export interface SupportTicket {
    id: string;
    tenant_id: string;
    title: string;
    description: string;
    status: SupportTicketStatus;
    priority: SupportTicketPriority;
    source: SupportTicketSource;
    company_id: string | null;
    company_name: string | null;
    contact_id: string | null;
    contact_name: string | null;
    assigned_to_user_id: string | null;
    assigned_to_full_name: string | null;
    assigned_to_email: string | null;
    related_deal_id: string | null;
    related_deal_name: string | null;
    related_invoice_id: string | null;
    related_invoice_number: string | null;
    created_at: string;
    updated_at: string;
}

export interface SupportTicketsListResponse {
    items: SupportTicket[];
    total: number;
}

export interface SupportTicketCreateRequest {
    title: string;
    description: string;
    status: SupportTicketStatus;
    priority: SupportTicketPriority;
    source: SupportTicketSource;
    company_id: string | null;
    contact_id: string | null;
    assigned_to_user_id: string | null;
    related_deal_id: string | null;
    related_invoice_id: string | null;
}

export interface SupportTicketUpdateRequest {
    title?: string | null;
    description?: string | null;
    status?: SupportTicketStatus | null;
    priority?: SupportTicketPriority | null;
    source?: SupportTicketSource | null;
    company_id?: string | null;
    contact_id?: string | null;
    assigned_to_user_id?: string | null;
    related_deal_id?: string | null;
    related_invoice_id?: string | null;
}

export interface SupportSummary {
    open_count: number;
    in_progress_count: number;
    urgent_count: number;
    resolved_this_period_count: number;
    report_period_start: string;
    report_period_end: string;
    generated_at: string;
}

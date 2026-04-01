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
    issue_date: string;
    due_date: string;
    currency: string;
    total_amount: string;
    status: InvoiceStatus;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface InvoicesListResponse {
    items: Invoice[];
    total: number;
}

export interface InvoiceCreateRequest {
    company_id: string;
    contact_id: string | null;
    product_id: string | null;
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

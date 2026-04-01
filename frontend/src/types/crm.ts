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

export interface DeleteResponse {
    success: boolean;
    message: string;
}

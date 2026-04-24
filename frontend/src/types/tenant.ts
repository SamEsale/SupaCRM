export type TenantStatus = "active" | "suspended" | "disabled";

export interface Tenant {
    id: string;
    name: string;
    is_active: boolean;
    status: TenantStatus;
    status_reason: string | null;
    legal_name: string | null;
    address_line_1: string | null;
    address_line_2: string | null;
    city: string | null;
    state_region: string | null;
    postal_code: string | null;
    country: string | null;
    vat_number: string | null;
    default_currency: string;
    secondary_currency: string | null;
    secondary_currency_rate: string | null;
    secondary_currency_rate_source: string | null;
    secondary_currency_rate_as_of: string | null;
    brand_primary_color: string | null;
    brand_secondary_color: string | null;
    sidebar_background_color: string | null;
    sidebar_text_color: string | null;
    logo_file_key: string | null;
    created_at: string;
    updated_at: string;
}

export interface TenantUpdateRequest {
    name: string;
    legal_name?: string | null;
    address_line_1?: string | null;
    address_line_2?: string | null;
    city?: string | null;
    state_region?: string | null;
    postal_code?: string | null;
    country?: string | null;
    vat_number?: string | null;
    default_currency: string;
    secondary_currency?: string | null;
    secondary_currency_rate?: string | null;
    brand_primary_color?: string | null;
    brand_secondary_color?: string | null;
    sidebar_background_color?: string | null;
    sidebar_text_color?: string | null;
}

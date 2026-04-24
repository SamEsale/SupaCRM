import { apiClient } from "@/lib/api-client";
import type { Tenant, TenantUpdateRequest } from "@/types/tenant";

export async function getCurrentTenant(): Promise<Tenant> {
    const response = await apiClient.get<Tenant>("/tenants/me");
    return response.data;
}

export async function updateCurrentTenant(
    payload: TenantUpdateRequest,
): Promise<Tenant> {
    const response = await apiClient.patch<Tenant>("/tenants/me", payload);
    return response.data;
}

export function buildTenantUpdatePayload(
    tenant: Tenant,
    overrides: Partial<TenantUpdateRequest> = {},
): TenantUpdateRequest {
    return {
        name: overrides.name ?? tenant.name,
        legal_name: overrides.legal_name ?? tenant.legal_name,
        address_line_1: overrides.address_line_1 ?? tenant.address_line_1,
        address_line_2: overrides.address_line_2 ?? tenant.address_line_2,
        city: overrides.city ?? tenant.city,
        state_region: overrides.state_region ?? tenant.state_region,
        postal_code: overrides.postal_code ?? tenant.postal_code,
        country: overrides.country ?? tenant.country,
        vat_number: overrides.vat_number ?? tenant.vat_number,
        default_currency: overrides.default_currency ?? tenant.default_currency,
        secondary_currency: overrides.secondary_currency ?? tenant.secondary_currency,
        secondary_currency_rate: overrides.secondary_currency_rate ?? tenant.secondary_currency_rate,
        brand_primary_color: overrides.brand_primary_color ?? tenant.brand_primary_color,
        brand_secondary_color: overrides.brand_secondary_color ?? tenant.brand_secondary_color,
        sidebar_background_color: overrides.sidebar_background_color ?? tenant.sidebar_background_color,
        sidebar_text_color: overrides.sidebar_text_color ?? tenant.sidebar_text_color,
    };
}

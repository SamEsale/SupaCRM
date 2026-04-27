import { apiClient } from "@/lib/api-client";
import type {
    TenantBranding,
    TenantBrandingUpdateRequest,
} from "@/types/settings";

export async function getTenantBranding(): Promise<TenantBranding> {
    const response = await apiClient.get<TenantBranding>("/tenants/me/branding");
    return response.data;
}

export async function updateTenantBranding(
    payload: TenantBrandingUpdateRequest,
): Promise<TenantBranding> {
    const response = await apiClient.put<TenantBranding>("/tenants/me/branding", payload);
    return response.data;
}


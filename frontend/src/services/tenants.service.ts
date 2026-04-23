import { apiClient } from "@/lib/api-client";
import type {
    CommercialSubscriptionStartRequest,
    Tenant,
    TenantMembershipMutationResponse,
    TenantMembershipRemovalResponse,
    TenantMembershipUpdateRequest,
    TenantOnboardingSummary,
    TenantRole,
    TenantRoleAssignmentBatchResponse,
    TenantRoleAssignmentRequest,
    TenantStatusUpdateRequest,
    TenantUpdateRequest,
    TenantUser,
    TenantUserProvisionRequest,
    TenantUserProvisionResponse,
} from "@/types/tenants";

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

export async function getTenantOnboardingSummary(): Promise<TenantOnboardingSummary> {
    const response = await apiClient.get<TenantOnboardingSummary>("/tenants/me/onboarding");
    return response.data;
}

export async function createTenantUser(
    payload: TenantUserProvisionRequest,
): Promise<TenantUserProvisionResponse> {
    const response = await apiClient.post<TenantUserProvisionResponse>("/tenants/me/users", payload);
    return response.data;
}

export async function getTenantUsers(): Promise<TenantUser[]> {
    const response = await apiClient.get<TenantUser[]>("/tenants/me/users");
    return response.data;
}

export async function getTenantRoles(): Promise<TenantRole[]> {
    const response = await apiClient.get<TenantRole[]>("/tenants/me/roles");
    return response.data;
}

export async function assignTenantUserRoles(
    userId: string,
    payload: TenantRoleAssignmentRequest,
): Promise<TenantRoleAssignmentBatchResponse> {
    const response = await apiClient.post<TenantRoleAssignmentBatchResponse>(
        `/tenants/me/users/${userId}/roles`,
        payload,
    );
    return response.data;
}

export async function updateTenantMembership(
    userId: string,
    payload: TenantMembershipUpdateRequest,
): Promise<TenantMembershipMutationResponse> {
    const response = await apiClient.patch<TenantMembershipMutationResponse>(
        `/tenants/me/users/${userId}/membership`,
        payload,
    );
    return response.data;
}

export async function removeTenantMembership(
    userId: string,
): Promise<TenantMembershipRemovalResponse> {
    const response = await apiClient.delete<TenantMembershipRemovalResponse>(
        `/tenants/me/users/${userId}/membership`,
    );
    return response.data;
}

export async function updateTenantStatus(
    payload: TenantStatusUpdateRequest,
): Promise<TenantOnboardingSummary["tenant"]> {
    const response = await apiClient.patch<TenantOnboardingSummary["tenant"]>("/tenants/me/status", payload);
    return response.data;
}

export async function startCommercialSubscription(
    payload: CommercialSubscriptionStartRequest,
): Promise<void> {
    await apiClient.post("/commercial/subscription", payload);
}

import { apiClient } from "@/lib/api-client";
import type {
    CommercialCheckoutSession,
    CommercialPlan,
    CommercialPaymentMethodListResponse,
    CommercialSubscription,
    CommercialSubscriptionStartRequest,
    CommercialSubscriptionSummary,
    TenantCommercialStatus,
} from "@/types/commercial";

export async function getCommercialPlans(): Promise<CommercialPlan[]> {
    const response = await apiClient.get<CommercialPlan[]>("/commercial/plans");
    return response.data;
}

export async function getPublicCommercialCatalog(): Promise<CommercialPlan[]> {
    const response = await apiClient.get<CommercialPlan[]>("/commercial/catalog");
    return response.data;
}

export async function getCommercialSubscriptionSummary(): Promise<CommercialSubscriptionSummary> {
    const response = await apiClient.get<CommercialSubscriptionSummary>("/commercial/subscription/summary");
    return response.data;
}

export async function getTenantCommercialStatus(): Promise<TenantCommercialStatus> {
    const response = await apiClient.get<TenantCommercialStatus>("/commercial/status");
    return response.data;
}

export async function startCommercialSubscription(
    payload: CommercialSubscriptionStartRequest,
): Promise<CommercialSubscription> {
    const response = await apiClient.post<CommercialSubscription>("/commercial/subscription", payload);
    return response.data;
}

export async function listCommercialPaymentMethods(): Promise<CommercialPaymentMethodListResponse> {
    const response = await apiClient.get<CommercialPaymentMethodListResponse>("/commercial/payment-methods");
    return response.data;
}

export async function createCommercialPaymentMethodCheckoutSession(payload: {
    customer_email?: string | null;
    customer_name?: string | null;
}): Promise<CommercialCheckoutSession> {
    const response = await apiClient.post<CommercialCheckoutSession>(
        "/commercial/payment-methods/checkout-session",
        payload,
    );
    return response.data;
}

export async function changeCommercialSubscriptionPlan(payload: {
    new_plan_code: string;
    prorate?: boolean;
}): Promise<CommercialSubscription> {
    const response = await apiClient.post<CommercialSubscription>("/commercial/subscription/change-plan", payload);
    return response.data;
}

export async function cancelCommercialSubscription(subscriptionId: string): Promise<CommercialSubscription> {
    const response = await apiClient.post<CommercialSubscription>(
        `/commercial/subscription/${subscriptionId}/cancel`,
        { state: "canceled" },
    );
    return response.data;
}

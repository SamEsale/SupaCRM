import { apiClient } from "@/lib/api-client";
import type {
    Deal,
    DealCreateRequest,
    DealUpdateRequest,
    DealsListResponse,
    DeleteResponse,
} from "@/types/crm";

export async function getDeals(): Promise<DealsListResponse> {
    const response = await apiClient.get<DealsListResponse>("/sales/deals");
    return response.data;
}

export async function createDeal(payload: DealCreateRequest): Promise<Deal> {
    const response = await apiClient.post<Deal>("/sales/deals", payload);
    return response.data;
}

export async function updateDeal(
    dealId: string,
    payload: DealUpdateRequest,
): Promise<Deal> {
    const response = await apiClient.patch<Deal>(`/sales/deals/${dealId}`, payload);
    return response.data;
}

export async function deleteDeal(dealId: string): Promise<DeleteResponse> {
    const response = await apiClient.delete<DeleteResponse>(`/sales/deals/${dealId}`);
    return response.data;
}

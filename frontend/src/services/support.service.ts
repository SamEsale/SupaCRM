import { apiClient } from "@/lib/api-client";
import type {
    SupportSummary,
    SupportTicket,
    SupportTicketCreateRequest,
    SupportTicketUpdateRequest,
    SupportTicketsListResponse,
} from "@/types/support";

export interface GetSupportTicketsParams {
    q?: string;
    status?: string;
    priority?: string;
    limit?: number;
    offset?: number;
}

export async function getSupportSummary(): Promise<SupportSummary> {
    const response = await apiClient.get<SupportSummary>("/support/summary");
    return response.data;
}

export async function getSupportTickets(
    params?: GetSupportTicketsParams,
): Promise<SupportTicketsListResponse> {
    const response = await apiClient.get<SupportTicketsListResponse>("/support/tickets", {
        params,
    });
    return response.data;
}

export async function getSupportTicketById(ticketId: string): Promise<SupportTicket> {
    const response = await apiClient.get<SupportTicket>(`/support/tickets/${ticketId}`);
    return response.data;
}

export async function createSupportTicket(
    payload: SupportTicketCreateRequest,
): Promise<SupportTicket> {
    const response = await apiClient.post<SupportTicket>("/support/tickets", payload);
    return response.data;
}

export async function updateSupportTicket(
    ticketId: string,
    payload: SupportTicketUpdateRequest,
): Promise<SupportTicket> {
    const response = await apiClient.patch<SupportTicket>(`/support/tickets/${ticketId}`, payload);
    return response.data;
}

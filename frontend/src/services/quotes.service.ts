import { apiClient } from "@/lib/api-client";
import type {
    QuoteDeleteResponse,
    Invoice,
    Quote,
    QuoteCreateRequest,
    QuoteUpdateRequest,
    QuotesListResponse,
    QuoteStatus,
} from "@/types/finance";

export interface GetQuotesParams {
    q?: string;
    status?: QuoteStatus;
    company_id?: string;
    number?: string;
    limit?: number;
    offset?: number;
}

export async function getQuotes(
    params?: GetQuotesParams,
): Promise<QuotesListResponse> {
    const response = await apiClient.get<QuotesListResponse>("/quotes", {
        params,
    });
    return response.data;
}

export async function getQuoteById(quoteId: string): Promise<Quote> {
    const response = await apiClient.get<Quote>(`/quotes/${quoteId}`);
    return response.data;
}

export async function createQuote(
    payload: QuoteCreateRequest,
): Promise<Quote> {
    const response = await apiClient.post<Quote>("/quotes", payload);
    return response.data;
}

export async function updateQuote(
    quoteId: string,
    payload: QuoteUpdateRequest,
): Promise<Quote> {
    const response = await apiClient.patch<Quote>(`/quotes/${quoteId}`, payload);
    return response.data;
}

export async function deleteQuote(
    quoteId: string,
): Promise<QuoteDeleteResponse> {
    const response = await apiClient.delete<QuoteDeleteResponse>(`/quotes/${quoteId}`);
    return response.data;
}

export async function updateQuoteStatus(
    quoteId: string,
    status: QuoteStatus,
): Promise<Quote> {
    const response = await apiClient.patch<Quote>(
        `/quotes/${quoteId}/status`,
        { status },
    );
    return response.data;
}

export async function convertQuoteToInvoice(quoteId: string): Promise<Invoice> {
    const response = await apiClient.post<Invoice>(`/quotes/${quoteId}/convert-to-invoice`);
    return response.data;
}

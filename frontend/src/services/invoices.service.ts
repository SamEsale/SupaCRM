import { apiClient } from "@/lib/api-client";
import type {
    InvoiceDeleteResponse,
    Invoice,
    InvoiceCreateRequest,
    InvoiceUpdateRequest,
    InvoicesListResponse,
    InvoiceStatus,
} from "@/types/finance";

export interface GetInvoicesParams {
    q?: string;
    status?: InvoiceStatus;
    company_id?: string;
    number?: string;
    source_quote_id?: string;
    limit?: number;
    offset?: number;
}

export async function getInvoices(
    params?: GetInvoicesParams,
): Promise<InvoicesListResponse> {
    const response = await apiClient.get<InvoicesListResponse>("/invoices", {
        params,
    });
    return response.data;
}

export async function getInvoiceById(invoiceId: string): Promise<Invoice> {
    const response = await apiClient.get<Invoice>(`/invoices/${invoiceId}`);
    return response.data;
}

export async function createInvoice(
    payload: InvoiceCreateRequest,
): Promise<Invoice> {
    const response = await apiClient.post<Invoice>("/invoices", payload);
    return response.data;
}

export async function updateInvoice(
    invoiceId: string,
    payload: InvoiceUpdateRequest,
): Promise<Invoice> {
    const response = await apiClient.patch<Invoice>(`/invoices/${invoiceId}`, payload);
    return response.data;
}

export async function updateInvoiceStatus(
    invoiceId: string,
    status: InvoiceStatus,
): Promise<Invoice> {
    const response = await apiClient.patch<Invoice>(
        `/invoices/${invoiceId}/status`,
        { status },
    );
    return response.data;
}

export async function deleteInvoice(
    invoiceId: string,
): Promise<InvoiceDeleteResponse> {
    const response = await apiClient.delete<InvoiceDeleteResponse>(`/invoices/${invoiceId}`);
    return response.data;
}

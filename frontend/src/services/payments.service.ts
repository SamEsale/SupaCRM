import { apiClient } from "@/lib/api-client";
import type {
    InvoicePayment,
    InvoicePaymentCreateRequest,
    InvoicePaymentListResponse,
    InvoicePaymentSummary,
    PaymentGatewayProvider,
    PaymentGatewayProviderUpdateRequest,
    PaymentGatewaySettingsSnapshot,
    PaymentMethod,
    PaymentProviderFoundationSnapshot,
    PaymentStatus,
} from "@/types/payments";

export interface GetPaymentsParams {
    invoice_id?: string;
    status?: PaymentStatus;
    method?: PaymentMethod;
    limit?: number;
    offset?: number;
}

export async function getPayments(
    params?: GetPaymentsParams,
): Promise<InvoicePaymentListResponse> {
    const response = await apiClient.get<InvoicePaymentListResponse>("/payments", {
        params,
    });
    return response.data;
}

export async function createPayment(
    payload: InvoicePaymentCreateRequest,
): Promise<InvoicePayment> {
    const response = await apiClient.post<InvoicePayment>("/payments", payload);
    return response.data;
}

export async function getInvoicePaymentSummary(
    invoiceId: string,
): Promise<InvoicePaymentSummary> {
    const response = await apiClient.get<InvoicePaymentSummary>(`/payments/invoices/${invoiceId}/summary`);
    return response.data;
}

export async function getPaymentGatewaySettings(): Promise<PaymentGatewaySettingsSnapshot> {
    const response = await apiClient.get<PaymentGatewaySettingsSnapshot>("/payments/gateway-settings");
    return response.data;
}

export async function updatePaymentGatewayProvider(
    provider: PaymentGatewayProvider,
    payload: PaymentGatewayProviderUpdateRequest,
): Promise<PaymentGatewaySettingsSnapshot> {
    const response = await apiClient.put<PaymentGatewaySettingsSnapshot>(
        `/payments/gateway-settings/${provider}`,
        payload,
    );
    return response.data;
}

export async function getPaymentProviderFoundation(): Promise<PaymentProviderFoundationSnapshot> {
    const response = await apiClient.get<PaymentProviderFoundationSnapshot>("/payments/provider-foundation");
    return response.data;
}

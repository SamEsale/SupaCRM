export type PaymentMethod =
    | "bank_transfer"
    | "cash"
    | "card_manual"
    | "other";

export type PaymentStatus =
    | "pending"
    | "completed"
    | "failed"
    | "cancelled";

export type InvoicePaymentState =
    | "unpaid"
    | "partially paid"
    | "paid";

export type PaymentGatewayProvider =
    | "stripe"
    | "revolut_business"
    | "payoneer";

export type PaymentGatewayMode =
    | "test"
    | "live";

export type PaymentGatewayConfigurationState =
    | "not_configured"
    | "incomplete"
    | "configured";

export type PaymentProviderFoundationState =
    | "disabled"
    | "needs_configuration"
    | "manual_only"
    | "ready";

export interface InvoicePayment {
    id: string;
    tenant_id: string;
    invoice_id: string;
    amount: string;
    currency: string;
    method: PaymentMethod;
    status: PaymentStatus;
    payment_date: string;
    external_reference: string | null;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface InvoicePaymentListResponse {
    items: InvoicePayment[];
    total: number;
}

export interface InvoicePaymentCreateRequest {
    invoice_id: string;
    amount: number;
    currency: string;
    method: PaymentMethod;
    status?: PaymentStatus;
    payment_date: string;
    external_reference?: string | null;
    notes?: string | null;
}

export interface InvoicePaymentSummary {
    invoice_id: string;
    currency: string;
    invoice_total_amount: string;
    completed_amount: string;
    pending_amount: string;
    outstanding_amount: string;
    payment_count: number;
    completed_payment_count: number;
    pending_payment_count: number;
    payment_state: InvoicePaymentState;
}

export interface PaymentStatusBreakdown {
    status: string;
    count: number;
    total_amount: string;
    currencies: string[];
}

export interface PaymentsSummary {
    payment_count: number;
    completed_payment_count: number;
    completed_payment_amount: string;
    pending_payment_count: number;
    failed_payment_count: number;
    cancelled_payment_count: number;
    payment_currencies: string[];
    generated_at: string;
}

export interface PaymentGatewayProviderSettings {
    provider: PaymentGatewayProvider;
    display_name: string;
    is_enabled: boolean;
    is_default: boolean;
    mode: PaymentGatewayMode;
    account_id: string | null;
    merchant_id: string | null;
    publishable_key: string | null;
    client_id: string | null;
    secret_key_set: boolean;
    api_key_set: boolean;
    client_secret_set: boolean;
    webhook_secret_set: boolean;
    configuration_state: PaymentGatewayConfigurationState;
    validation_errors: string[];
    updated_at: string | null;
}

export interface PaymentGatewaySettingsSnapshot {
    default_provider: PaymentGatewayProvider | null;
    providers: PaymentGatewayProviderSettings[];
    updated_at: string | null;
}

export interface PaymentGatewayProviderUpdateRequest {
    is_enabled: boolean;
    is_default: boolean;
    mode: PaymentGatewayMode;
    account_id?: string | null;
    merchant_id?: string | null;
    publishable_key?: string | null;
    client_id?: string | null;
    secret_key?: string | null;
    api_key?: string | null;
    client_secret?: string | null;
    webhook_secret?: string | null;
}

export interface PaymentProviderFoundation {
    provider: PaymentGatewayProvider;
    display_name: string;
    is_enabled: boolean;
    is_default: boolean;
    mode: PaymentGatewayMode;
    configuration_state: PaymentGatewayConfigurationState;
    foundation_state: PaymentProviderFoundationState;
    supports_checkout_payments: boolean;
    supports_webhooks: boolean;
    supports_automated_subscriptions: boolean;
    operator_summary: string;
    validation_errors: string[];
    updated_at: string | null;
}

export interface PaymentProviderFoundationSnapshot {
    default_provider: PaymentGatewayProvider | null;
    providers: PaymentProviderFoundation[];
    updated_at: string | null;
}

export type CommercialState =
    | "pending"
    | "trial"
    | "active"
    | "past_due"
    | "grace"
    | "suspended"
    | "canceled";

export type BillingCycleStatus =
    | "pending"
    | "issued"
    | "paid"
    | "past_due"
    | "grace"
    | "suspended"
    | "canceled"
    | "void";

export type BillingEventStatus =
    | "received"
    | "processing"
    | "processed"
    | "failed";

export interface CommercialPlan {
    id: string;
    code: string;
    plan_code: string;
    name: string;
    description: string | null;
    provider: string;
    provider_price_id: string | null;
    billing_interval: string;
    price_amount: string;
    currency: string;
    trial_days: number;
    grace_days: number;
    is_active: boolean;
    features: Record<string, unknown>;
    features_summary: string[];
    created_at: string;
    updated_at: string;
}

export interface CommercialSubscription {
    id: string;
    tenant_id: string;
    plan_id: string;
    plan_code: string;
    plan_name: string;
    provider: string;
    provider_customer_id: string | null;
    provider_subscription_id: string | null;
    subscription_status: string | null;
    commercial_state: CommercialState;
    state_reason: string | null;
    trial_start_at: string | null;
    trial_end_at: string | null;
    current_period_start_at: string | null;
    current_period_end_at: string | null;
    grace_end_at: string | null;
    cancel_at_period_end: boolean;
    activated_at: string | null;
    reactivated_at: string | null;
    suspended_at: string | null;
    canceled_at: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
    updated_at: string;
}

export interface CommercialBillingCycleSummary {
    id: string;
    cycle_number: number;
    period_start_at: string;
    period_end_at: string;
    due_at: string;
    amount: string;
    currency: string;
    status: BillingCycleStatus;
    invoice_id: string | null;
    created_at: string;
}

export interface CommercialBillingEventSummary {
    id: string;
    provider: string;
    external_event_id: string;
    event_type: string;
    processing_status: BillingEventStatus;
    action_taken: string | null;
    error_message: string | null;
    processed_at: string | null;
    created_at: string;
}

export interface CommercialSubscriptionSummary {
    subscription: CommercialSubscription | null;
    recent_billing_cycles: CommercialBillingCycleSummary[];
    recent_billing_events: CommercialBillingEventSummary[];
}

export interface TenantCommercialStatus {
    current_plan: CommercialPlan | null;
    subscription: CommercialSubscription | null;
    subscription_status: string | null;
    trial_status: "active" | "ended" | "not_applicable";
    next_billing_at: string | null;
    renewal_at: string | null;
    provider: string | null;
    provider_name: string | null;
    provider_customer_id: string | null;
    provider_subscription_id: string | null;
    commercially_active: boolean;
}

export interface CommercialSubscriptionStartRequest {
    plan_code: string;
    provider: string;
    start_trial: boolean;
    customer_email?: string | null;
    customer_name?: string | null;
}

export interface CommercialPaymentMethod {
    id: string;
    tenant_id: string;
    provider_customer_id: string;
    provider_payment_method_id: string;
    provider_type: string;
    card_brand: string | null;
    card_last4: string | null;
    card_exp_month: number | null;
    card_exp_year: number | null;
    billing_email: string | null;
    billing_name: string | null;
    is_default: boolean;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface CommercialPaymentMethodListResponse {
    items: CommercialPaymentMethod[];
    total: number;
}

export interface CommercialCheckoutSession {
    provider: string;
    session_id: string;
    url: string;
    mode: "setup" | "subscription";
    provider_customer_id: string | null;
    provider_subscription_id: string | null;
}

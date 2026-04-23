import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    cancelCommercialSubscription: vi.fn(),
    changeCommercialSubscriptionPlan: vi.fn(),
    createCommercialPaymentMethodCheckoutSession: vi.fn(),
    getCommercialPlans: vi.fn(),
    getCommercialSubscriptionSummary: vi.fn(),
    getTenantCommercialStatus: vi.fn(),
    listCommercialPaymentMethods: vi.fn(),
    startCommercialSubscription: vi.fn(),
    getPaymentProviderFoundation: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "access-token",
        refreshToken: "refresh-token",
        user: {
            tenant_id: "tenant-1",
            email: "owner@example.com",
            full_name: "Owner User",
        },
    }),
}));

vi.mock("@/services/commercial.service", () => ({
    cancelCommercialSubscription: mocks.cancelCommercialSubscription,
    changeCommercialSubscriptionPlan: mocks.changeCommercialSubscriptionPlan,
    createCommercialPaymentMethodCheckoutSession: mocks.createCommercialPaymentMethodCheckoutSession,
    getCommercialPlans: mocks.getCommercialPlans,
    getCommercialSubscriptionSummary: mocks.getCommercialSubscriptionSummary,
    getTenantCommercialStatus: mocks.getTenantCommercialStatus,
    listCommercialPaymentMethods: mocks.listCommercialPaymentMethods,
    startCommercialSubscription: mocks.startCommercialSubscription,
}));

vi.mock("@/services/payments.service", () => ({
    getPaymentProviderFoundation: mocks.getPaymentProviderFoundation,
}));

import SubscriptionBillingPage from "@/app/(dashboard)/finance/payments/subscription-billing/page";

const basePlans = [
    {
        id: "plan-growth",
        code: "growth",
        plan_code: "growth",
        name: "Growth",
        description: "Growth plan",
        provider: "stripe",
        provider_price_id: "price_growth",
        billing_interval: "month",
        price_amount: "49.00",
        currency: "USD",
        trial_days: 14,
        grace_days: 7,
        is_active: true,
        features: {},
        features_summary: ["CRM core", "Stripe billing"],
        created_at: "2026-04-22T10:00:00.000Z",
        updated_at: "2026-04-22T10:00:00.000Z",
    },
    {
        id: "plan-scale",
        code: "scale",
        plan_code: "scale",
        name: "Scale",
        description: "Scale plan",
        provider: "stripe",
        provider_price_id: "price_scale",
        billing_interval: "year",
        price_amount: "199.00",
        currency: "USD",
        trial_days: 14,
        grace_days: 7,
        is_active: true,
        features: {},
        features_summary: ["CRM core", "Priority support"],
        created_at: "2026-04-22T10:00:00.000Z",
        updated_at: "2026-04-22T10:00:00.000Z",
    },
];

const baseSubscription = {
    id: "sub-1",
    tenant_id: "tenant-1",
    plan_id: "plan-growth",
    plan_code: "growth",
    plan_name: "Growth",
    provider: "stripe",
    provider_customer_id: "cus_123",
    provider_subscription_id: "sub_123",
    subscription_status: "trialing",
    commercial_state: "trial" as const,
    state_reason: null,
    trial_start_at: "2026-04-22T10:00:00.000Z",
    trial_end_at: "2026-05-06T10:00:00.000Z",
    current_period_start_at: "2026-04-22T10:00:00.000Z",
    current_period_end_at: "2026-05-22T10:00:00.000Z",
    grace_end_at: null,
    cancel_at_period_end: false,
    activated_at: null,
    reactivated_at: null,
    suspended_at: null,
    canceled_at: null,
    metadata: {},
    created_at: "2026-04-22T10:00:00.000Z",
    updated_at: "2026-04-22T10:00:00.000Z",
};

const baseSummary = {
    subscription: baseSubscription,
    recent_billing_cycles: [],
    recent_billing_events: [],
};

const baseCommercialStatus = {
    current_plan: null,
    subscription: null,
    subscription_status: "trialing",
    trial_status: "active" as const,
    next_billing_at: null,
    renewal_at: "2026-05-22T10:00:00.000Z",
    provider: "stripe",
    provider_name: "Stripe",
    provider_customer_id: "cus_123",
    provider_subscription_id: "sub_123",
    commercially_active: true,
};

const basePaymentMethods = {
    items: [
        {
            id: "pm-1",
            tenant_id: "tenant-1",
            provider_customer_id: "cus_123",
            provider_payment_method_id: "pm_123",
            provider_type: "stripe",
            card_brand: "visa",
            card_last4: "4242",
            card_exp_month: 5,
            card_exp_year: 2030,
            billing_email: "owner@example.com",
            billing_name: "Owner User",
            is_default: true,
            is_active: true,
            created_at: "2026-04-22T10:00:00.000Z",
            updated_at: "2026-04-22T10:00:00.000Z",
        },
    ],
    total: 1,
};

const baseFoundation = {
    default_provider: "stripe",
    updated_at: "2026-04-22T10:00:00.000Z",
    providers: [
        {
            provider: "stripe",
            display_name: "Stripe",
            is_enabled: true,
            is_default: true,
            mode: "live",
            configuration_state: "configured",
            foundation_state: "ready",
            supports_checkout_payments: true,
            supports_webhooks: true,
            supports_automated_subscriptions: true,
            operator_summary: "Stripe is ready.",
            validation_errors: [],
            updated_at: "2026-04-22T10:00:00.000Z",
        },
    ],
};

function mockWorkspace(overrides?: {
    summary?: Record<string, unknown>;
    commercialStatus?: Record<string, unknown>;
    paymentMethods?: Record<string, unknown>;
}) {
    mocks.getCommercialPlans.mockResolvedValue(basePlans);
    mocks.getCommercialSubscriptionSummary.mockResolvedValue(overrides?.summary ?? baseSummary);
    mocks.getTenantCommercialStatus.mockResolvedValue(overrides?.commercialStatus ?? baseCommercialStatus);
    mocks.listCommercialPaymentMethods.mockResolvedValue(overrides?.paymentMethods ?? basePaymentMethods);
    mocks.getPaymentProviderFoundation.mockResolvedValue(baseFoundation);
}

describe("SubscriptionBillingPage", () => {
    const assignMock = vi.fn();

    beforeEach(() => {
        Object.defineProperty(window, "location", {
            value: { assign: assignMock },
            writable: true,
        });

        Object.values(mocks).forEach((mock) => mock.mockReset());
        mockWorkspace();

        mocks.startCommercialSubscription.mockResolvedValue({});
        mocks.changeCommercialSubscriptionPlan.mockResolvedValue({});
        mocks.cancelCommercialSubscription.mockResolvedValue({});
        mocks.createCommercialPaymentMethodCheckoutSession.mockResolvedValue({
            provider: "stripe",
            session_id: "cs_123",
            url: "https://stripe.test/session",
            mode: "setup",
            provider_customer_id: "cus_123",
            provider_subscription_id: null,
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("uses the existing trial-to-paid conversion path when the tenant is trialing", async () => {
        render(<SubscriptionBillingPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Subscription Billing" })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /convert trial to paid/i }));

        await waitFor(() => {
            expect(mocks.startCommercialSubscription).toHaveBeenCalledWith({
                plan_code: "growth",
                provider: "stripe",
                start_trial: false,
                customer_email: "owner@example.com",
                customer_name: "Owner User",
            });
        });
    });

    it("creates a Stripe setup checkout session when payment method capture is requested", async () => {
        render(<SubscriptionBillingPage />);

        await waitFor(() => {
            expect(screen.getAllByRole("button", { name: /update payment method/i }).length).toBeGreaterThan(0);
        });

        fireEvent.click(screen.getAllByRole("button", { name: /update payment method/i })[0]);

        await waitFor(() => {
            expect(mocks.createCommercialPaymentMethodCheckoutSession).toHaveBeenCalledWith({
                customer_email: "owner@example.com",
                customer_name: "Owner User",
            });
            expect(assignMock).toHaveBeenCalledWith("https://stripe.test/session");
        });
    });

    it("renders a clear past-due recovery state with an update payment method CTA", async () => {
        mockWorkspace({
            summary: {
                ...baseSummary,
                subscription: {
                    ...baseSubscription,
                    subscription_status: "past_due",
                    commercial_state: "past_due",
                    grace_end_at: "2026-04-30T10:00:00.000Z",
                },
            },
            commercialStatus: {
                ...baseCommercialStatus,
                subscription_status: "past_due",
                commercially_active: true,
            },
        });

        render(<SubscriptionBillingPage />);

        await waitFor(() => {
            expect(screen.getAllByText("Past Due").length).toBeGreaterThan(0);
            expect(screen.getByText(/stripe has reported a failed payment/i)).toBeTruthy();
            expect(screen.getAllByRole("button", { name: /update payment method/i }).length).toBeGreaterThan(0);
        });
    });

    it("renders a payment method missing state with an add payment method CTA", async () => {
        mockWorkspace({
            paymentMethods: { items: [], total: 0 },
        });

        render(<SubscriptionBillingPage />);

        await waitFor(() => {
            expect(screen.getAllByText("Payment Method Missing").length).toBeGreaterThan(0);
            expect(screen.getAllByRole("button", { name: /add payment method/i }).length).toBeGreaterThan(0);
        });
    });

    it("renders the active state truthfully and does not offer a fake restart button for an existing paid subscription", async () => {
        mockWorkspace({
            summary: {
                ...baseSummary,
                subscription: {
                    ...baseSubscription,
                    subscription_status: "active",
                    commercial_state: "active",
                    trial_end_at: null,
                    activated_at: "2026-04-22T10:00:00.000Z",
                },
            },
            commercialStatus: {
                ...baseCommercialStatus,
                subscription_status: "active",
                trial_status: "not_applicable",
            },
        });

        render(<SubscriptionBillingPage />);

        await waitFor(() => {
            expect(screen.getAllByText("Active").length).toBeGreaterThan(0);
            expect(screen.getByText(/stripe currently reports the tenant as active/i)).toBeTruthy();
        });

        expect(screen.queryByRole("button", { name: /^start subscription$/i })).toBeNull();
        expect(screen.queryByRole("button", { name: /convert trial to paid/i })).toBeNull();
    });
});

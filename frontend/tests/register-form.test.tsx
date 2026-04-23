import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: pushMock,
        refresh: refreshMock,
    }),
}));

vi.mock("@/services/commercial.service", () => ({
    getPublicCommercialCatalog: vi.fn(),
}));

vi.mock("@/services/auth.service", () => ({
    register: vi.fn(),
    getCurrentUser: vi.fn(),
}));

vi.mock("@/lib/auth-storage", () => ({
    setAuthStorage: vi.fn(),
    setTenantId: vi.fn(),
    setTokenStorage: vi.fn(),
}));

import RegisterForm from "@/components/auth/register-form";
import { getCurrentUser, register } from "@/services/auth.service";
import { getPublicCommercialCatalog } from "@/services/commercial.service";

describe("RegisterForm", () => {
    beforeEach(() => {
        pushMock.mockReset();
        refreshMock.mockReset();

        vi.mocked(getPublicCommercialCatalog).mockResolvedValue([
            {
                id: "plan-1",
                code: "starter",
                plan_code: "starter",
                name: "Starter",
                description: "Starter",
                provider: "stripe",
                provider_price_id: null,
                billing_interval: "month",
                price_amount: "0.00",
                currency: "USD",
                trial_days: 14,
                grace_days: 7,
                is_active: true,
                features: {},
                features_summary: ["CRM core", "Billing visibility"],
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            },
            {
                id: "plan-2",
                code: "starter_yearly",
                plan_code: "starter_yearly",
                name: "Starter Yearly",
                description: "Starter yearly",
                provider: "stripe",
                provider_price_id: null,
                billing_interval: "year",
                price_amount: "0.00",
                currency: "USD",
                trial_days: 14,
                grace_days: 7,
                is_active: true,
                features: {},
                features_summary: ["CRM core", "Billing visibility"],
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            },
        ]);

        vi.mocked(register).mockResolvedValue({
            access_token: "access-token",
            refresh_token: "refresh-token",
            tenant_id: "acme",
            tenant_name: "Acme",
            token_type: "bearer",
            access_token_expires_at: new Date().toISOString(),
            refresh_token_expires_at: new Date().toISOString(),
            commercial_status: {
                current_plan: null,
                subscription: null,
                subscription_status: "trial",
                trial_status: "active",
                next_billing_at: null,
                renewal_at: null,
                provider: "stripe",
                provider_name: "Stripe",
                provider_customer_id: null,
                provider_subscription_id: null,
                commercially_active: true,
            },
        });

        vi.mocked(getCurrentUser).mockResolvedValue({
            user_id: "user-1",
            tenant_id: "acme",
            email: "owner@example.com",
            full_name: "Owner User",
            roles: ["owner"],
            is_owner: true,
            user_is_active: true,
            membership_is_active: true,
            tenant_is_active: true,
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("loads the public plan catalog and registers a tenant on the selected plan", async () => {
        render(<RegisterForm />);

        await waitFor(() => {
            expect(screen.getByText(/starter yearly/i)).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /starter yearly/i }));
        fireEvent.change(screen.getByLabelText(/company name/i), {
            target: { value: "Acme" },
        });
        fireEvent.change(screen.getByLabelText(/your name/i), {
            target: { value: "Owner User" },
        });
        fireEvent.change(screen.getByLabelText(/work email/i), {
            target: { value: "owner@example.com" },
        });
        fireEvent.change(screen.getByLabelText(/password/i), {
            target: { value: "Password1234!" },
        });

        fireEvent.submit(screen.getByRole("button", { name: /create workspace/i }));

        await waitFor(() => {
            expect(register).toHaveBeenCalledWith(
                expect.objectContaining({
                    company_name: "Acme",
                    full_name: "Owner User",
                    email: "owner@example.com",
                    plan_code: "starter_yearly",
                    provider: "stripe",
                    start_trial: true,
                }),
            );
        });

        expect(getCurrentUser).toHaveBeenCalledWith("acme");
        expect(pushMock).toHaveBeenCalledWith("/dashboard");
        expect(refreshMock).toHaveBeenCalledTimes(1);
    });
});

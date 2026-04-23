import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getTenantOnboardingSummary: vi.fn(),
    createTenantUser: vi.fn(),
    startCommercialSubscription: vi.fn(),
    updateTenantStatus: vi.fn(),
}));

vi.mock("@/services/tenants.service", () => ({
    getTenantOnboardingSummary: mocks.getTenantOnboardingSummary,
    createTenantUser: mocks.createTenantUser,
    startCommercialSubscription: mocks.startCommercialSubscription,
    updateTenantStatus: mocks.updateTenantStatus,
}));

import OnboardingPage from "@/app/(dashboard)/onboarding/page";
import type { TenantOnboardingSummary } from "@/types/tenants";

function buildReadySummary(): TenantOnboardingSummary {
    return {
        tenant: {
            id: "tenant-1",
            name: "Tenant 1",
            is_active: true,
            status: "active",
            status_reason: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        },
        commercial_subscription: {
            id: "sub-1",
            plan_code: "starter",
            plan_name: "Starter",
            commercial_state: "trial",
            plan_features: {
                tier: "starter",
                self_service: true,
                included_capabilities: ["CRM core"],
                launch_limitations: ["Marketing automation remains staged"],
            },
            trial_end_at: null,
            current_period_end_at: null,
            grace_end_at: null,
            canceled_at: null,
        },
        users_total: 1,
        owner_count: 1,
        admin_count: 1,
        bootstrap_complete: true,
        ready_for_use: true,
        missing_steps: [],
        warnings: [],
        next_action: "ready",
    };
}

beforeEach(() => {
    mocks.getTenantOnboardingSummary.mockResolvedValue(buildReadySummary());
    mocks.createTenantUser.mockResolvedValue(undefined);
    mocks.startCommercialSubscription.mockRejectedValue(
        new Error("Request failed with status code 400"),
    );
    mocks.updateTenantStatus.mockResolvedValue(undefined);
});

afterEach(() => {
    cleanup();
});

describe("onboarding page error handling", () => {
    it("keeps a ready tenant page clean when a secondary action fails", async () => {
        render(<OnboardingPage />);

        await waitFor(() => {
            expect(screen.getByText(/tenant is ready/i)).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /start starter trial/i }));

        await waitFor(() => {
            expect(screen.getByText(/failed to start subscription\./i)).toBeTruthy();
        });

        expect(
            screen.queryByText(/request failed with status code 400/i),
        ).toBeNull();
        expect(screen.getByText(/tenant is ready/i)).toBeTruthy();
    });
});

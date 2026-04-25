import { describe, expect, it } from "vitest";

import { summarizeOnboardingState } from "@/components/onboarding/onboarding-utils";
import type { TenantOnboardingSummary } from "@/types/tenants";

function buildSummary(overrides: Partial<TenantOnboardingSummary> = {}): TenantOnboardingSummary {
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
                included_capabilities: ["CRM core", "Sales, quotes, and invoices"],
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
        ...overrides,
    };
}

describe("onboarding state presentation", () => {
    it("describes a ready tenant as ready", () => {
        const presentation = summarizeOnboardingState(buildSummary());

        expect(presentation.title).toBe("Tenant is ready");
        expect(presentation.primaryActionLabel).toBe("Review details");
        expect(presentation.stateTone).toBe("ready");
    });

    it("surfaces the first missing admin as the primary action", () => {
        const presentation = summarizeOnboardingState(
            buildSummary({
                owner_count: 0,
                admin_count: 0,
                bootstrap_complete: false,
                ready_for_use: false,
                missing_steps: ["first_admin_missing", "commercial_subscription_missing"],
                commercial_subscription: null,
                next_action: "create_first_admin",
            }),
        );

        expect(presentation.title).toBe("First admin still needed");
        expect(presentation.primaryActionLabel).toBe("Create admin");
        expect(presentation.stateTone).toBe("blocked");
    });
});

import { describe, expect, it } from "vitest";

import { summarizeLaunchPackaging } from "@/components/onboarding/launch-packaging";
import type { TenantCommercialSubscription } from "@/types/tenants";

function buildSubscription(
    overrides: Partial<TenantCommercialSubscription> = {},
): TenantCommercialSubscription {
    return {
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
        ...overrides,
    };
}

describe("launch packaging presentation", () => {
    it("summarizes the current launch package from plan features", () => {
        const presentation = summarizeLaunchPackaging(buildSubscription());

        expect(presentation.title).toBe("Starter launch package");
        expect(presentation.tierLabel).toBe("starter");
        expect(presentation.includedCapabilities).toContain("CRM core");
        expect(presentation.launchLimitations).toContain("Marketing automation remains staged");
    });

    it("falls back cleanly when no subscription is present", () => {
        const presentation = summarizeLaunchPackaging(null);

        expect(presentation.title).toBe("Launch package unavailable");
        expect(presentation.tierLabel).toBe("Unassigned");
        expect(presentation.includedCapabilities).toEqual([]);
        expect(presentation.launchLimitations).toEqual([]);
    });
});

import type { TenantOnboardingSummary } from "@/types/tenants";

export interface OnboardingPresentation {
    title: string;
    description: string;
    primaryActionLabel: string;
    stateTone: "ready" | "warning" | "blocked";
}

export function summarizeOnboardingState(
    summary: TenantOnboardingSummary | null,
): OnboardingPresentation {
    if (!summary) {
        return {
            title: "Loading onboarding state",
            description: "Fetching tenant setup details.",
            primaryActionLabel: "Refresh",
            stateTone: "warning",
        };
    }

    if (summary.bootstrap_complete && summary.ready_for_use) {
        return {
            title: "Tenant is ready",
            description: "The first admin and commercial subscription are in place.",
            primaryActionLabel: "Review details",
            stateTone: "ready",
        };
    }

    if (summary.missing_steps.includes("tenant_not_active")) {
        return {
            title: "Tenant needs activation",
            description: "Bring the tenant back to an active state before users can work.",
            primaryActionLabel: "Activate tenant",
            stateTone: "blocked",
        };
    }

    if (summary.missing_steps.includes("first_admin_missing")) {
        return {
            title: "First admin still needed",
            description: "Create the initial admin account to complete onboarding.",
            primaryActionLabel: "Create admin",
            stateTone: "blocked",
        };
    }

    if (summary.missing_steps.includes("commercial_subscription_missing")) {
        return {
            title: "Commercial subscription missing",
            description: "Start the starter trial to make the tenant usable.",
            primaryActionLabel: "Start trial",
            stateTone: "blocked",
        };
    }

    if (summary.missing_steps.some((step) => step.startsWith("commercial_"))) {
        return {
            title: "Commercial access needs attention",
            description: "The subscription is suspended or canceled and must be reactivated.",
            primaryActionLabel: "Reactivate subscription",
            stateTone: "blocked",
        };
    }

    if (summary.warnings.includes("billing_attention_required")) {
        return {
            title: "Billing attention required",
            description: "The tenant is usable, but the subscription needs operator review.",
            primaryActionLabel: "Review billing",
            stateTone: "warning",
        };
    }

    return {
        title: "Onboarding in progress",
        description: "Review the remaining setup items below.",
        primaryActionLabel: "Review setup",
        stateTone: "warning",
    };
}

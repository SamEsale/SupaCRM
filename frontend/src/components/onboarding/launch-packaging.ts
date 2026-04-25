import type { TenantCommercialSubscription } from "@/types/tenants";

export interface LaunchPackagingPresentation {
    title: string;
    description: string;
    tierLabel: string;
    includedCapabilities: string[];
    launchLimitations: string[];
}

export function summarizeLaunchPackaging(
    subscription: TenantCommercialSubscription | null,
): LaunchPackagingPresentation {
    if (!subscription) {
        return {
            title: "Launch package unavailable",
            description: "Start a commercial subscription to show the launch package.",
            tierLabel: "Unassigned",
            includedCapabilities: [],
            launchLimitations: [],
        };
    }

    const includedCapabilities = Array.isArray(subscription.plan_features.included_capabilities)
        ? subscription.plan_features.included_capabilities
        : [];
    const launchLimitations = Array.isArray(subscription.plan_features.launch_limitations)
        ? subscription.plan_features.launch_limitations
        : [];

    return {
        title: `${subscription.plan_name} launch package`,
        description:
            "This packaging is grounded in the active plan features currently deployed in SupaCRM.",
        tierLabel: subscription.plan_features.tier ? String(subscription.plan_features.tier) : subscription.plan_code,
        includedCapabilities,
        launchLimitations,
    };
}

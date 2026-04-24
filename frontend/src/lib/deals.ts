import type { Deal, DealStage, DealStatus, LeadSource } from "@/types/crm";

export const DEAL_STAGES: DealStage[] = [
    "new lead",
    "qualified lead",
    "proposal sent",
    "estimate sent",
    "negotiating contract terms",
    "contract signed",
    "deal not secured",
];

export const DEAL_STATUSES: DealStatus[] = [
    "open",
    "in progress",
    "won",
    "lost",
];

export const LEAD_SOURCES: LeadSource[] = [
    "manual",
    "website",
    "email",
    "phone",
    "referral",
    "whatsapp",
    "other",
];

export const OPPORTUNITY_DEAL_STAGES: DealStage[] = [
    "qualified lead",
    "proposal sent",
    "estimate sent",
    "negotiating contract terms",
];

export const OPPORTUNITY_DEAL_STATUSES: DealStatus[] = [
    "open",
    "in progress",
];

export const DEAL_STAGE_FORECAST_WEIGHTS: Record<DealStage, number> = {
    "new lead": 0.1,
    "qualified lead": 0.25,
    "proposal sent": 0.5,
    "estimate sent": 0.6,
    "negotiating contract terms": 0.8,
    "contract signed": 1,
    "deal not secured": 0,
};

export const PIPELINE_STAGE_TRANSITIONS: Record<DealStage, DealStage[]> = {
    "new lead": ["qualified lead", "deal not secured"],
    "qualified lead": ["proposal sent", "estimate sent", "deal not secured"],
    "proposal sent": ["negotiating contract terms", "contract signed", "deal not secured"],
    "estimate sent": ["negotiating contract terms", "contract signed", "deal not secured"],
    "negotiating contract terms": ["contract signed", "deal not secured"],
    "contract signed": [],
    "deal not secured": [],
};

export function formatDealLabel(value: string): string {
    return value
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

export function suggestStatusForStage(
    stage: DealStage,
    currentStatus: DealStatus,
): DealStatus {
    if (stage === "contract signed") {
        return "won";
    }

    if (stage === "deal not secured") {
        return "lost";
    }

    if (currentStatus === "won" || currentStatus === "lost") {
        return "in progress";
    }

    return currentStatus;
}

export function isOpportunityDeal(stage: DealStage, status: DealStatus): boolean {
    return OPPORTUNITY_DEAL_STAGES.includes(stage) && OPPORTUNITY_DEAL_STATUSES.includes(status);
}

export function isActivePipelineStatus(status: DealStatus): boolean {
    return status === "open" || status === "in progress";
}

export type DealFollowUpState = "closed" | "overdue" | "due-today" | "upcoming" | "unscheduled";

export function getDealFollowUpState(
    deal: Pick<Deal, "status" | "next_follow_up_at">,
    now: Date = new Date(),
): DealFollowUpState {
    if (!isActivePipelineStatus(deal.status)) {
        return "closed";
    }

    if (!deal.next_follow_up_at) {
        return "unscheduled";
    }

    const followUpDate = new Date(deal.next_follow_up_at);
    if (Number.isNaN(followUpDate.getTime())) {
        return "unscheduled";
    }

    if (followUpDate.getTime() < now.getTime()) {
        return "overdue";
    }

    if (followUpDate.toDateString() === now.toDateString()) {
        return "due-today";
    }

    return "upcoming";
}

export function getDealFollowUpLabel(
    deal: Pick<Deal, "status" | "next_follow_up_at">,
    now: Date = new Date(),
): string {
    const state = getDealFollowUpState(deal, now);

    if (state === "closed") {
        return "Closed";
    }
    if (state === "unscheduled") {
        return "Not scheduled";
    }
    if (state === "due-today") {
        return "Due today";
    }
    if (state === "overdue") {
        return "Overdue";
    }
    return "Upcoming";
}


import { apiClient } from "@/lib/api-client";
import type { RecentAuditActivityListResponse } from "@/types/audit";

export async function getRecentAuditActivity(
    limit = 10,
): Promise<RecentAuditActivityListResponse> {
    const response = await apiClient.get<RecentAuditActivityListResponse>("/audit/recent", {
        params: { limit },
    });
    return response.data;
}

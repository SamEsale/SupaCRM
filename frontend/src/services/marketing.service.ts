import { apiClient } from "@/lib/api-client";
import type { CsvDownloadResult } from "@/services/contacts.service";
import type {
    MarketingCampaign,
    MarketingCampaignAudiencePreview,
    MarketingCampaignDetail,
    MarketingCampaignExecutionDetail,
    MarketingExecutionFollowUpHandoffRequest,
    MarketingExecutionFollowUpHandoffResponse,
    MarketingCampaignListResponse,
    MarketingCampaignStatus,
    MarketingExecutionRecipientResultFilter,
    MarketingCampaignUpsertRequest,
    WhatsAppLeadIntakeRequest,
    WhatsAppLeadIntakeResponse,
} from "@/types/marketing";

export interface GetMarketingCampaignsParams {
    q?: string;
    channel?: "email" | "whatsapp";
    status?: MarketingCampaignStatus;
    limit?: number;
    offset?: number;
}

export interface GetMarketingCampaignAudiencePreviewParams {
    sample_limit?: number;
}

export interface GetMarketingCampaignExecutionDetailParams {
    recipient_status?: MarketingExecutionRecipientResultFilter;
}

function parseFilename(headerValue: string | undefined, fallback: string): string {
    if (!headerValue) {
        return fallback;
    }

    const match = headerValue.match(/filename="?([^"]+)"?/i);
    return match?.[1] ?? fallback;
}

export async function getMarketingCampaigns(
    params?: GetMarketingCampaignsParams,
): Promise<MarketingCampaignListResponse> {
    const response = await apiClient.get<MarketingCampaignListResponse>("/marketing/campaigns", {
        params,
    });
    return response.data;
}

export async function createMarketingCampaign(
    payload: MarketingCampaignUpsertRequest,
): Promise<MarketingCampaign> {
    const response = await apiClient.post<MarketingCampaign>("/marketing/campaigns", payload);
    return response.data;
}

export async function updateMarketingCampaign(
    campaignId: string,
    payload: MarketingCampaignUpsertRequest,
): Promise<MarketingCampaign> {
    const response = await apiClient.put<MarketingCampaign>(
        `/marketing/campaigns/${campaignId}`,
        payload,
    );
    return response.data;
}

export async function getMarketingCampaignAudiencePreview(
    campaignId: string,
    params?: GetMarketingCampaignAudiencePreviewParams,
): Promise<MarketingCampaignAudiencePreview> {
    const response = await apiClient.get<MarketingCampaignAudiencePreview>(
        `/marketing/campaigns/${campaignId}/audience-preview`,
        {
            params,
        },
    );
    return response.data;
}

export async function getMarketingCampaignDetail(
    campaignId: string,
): Promise<MarketingCampaignDetail> {
    const response = await apiClient.get<MarketingCampaignDetail>(
        `/marketing/campaigns/${campaignId}`,
    );
    return response.data;
}

export async function getMarketingCampaignExecutionDetail(
    campaignId: string,
    executionId: string,
    params?: GetMarketingCampaignExecutionDetailParams,
): Promise<MarketingCampaignExecutionDetail> {
    const response = await apiClient.get<MarketingCampaignExecutionDetail>(
        `/marketing/campaigns/${campaignId}/executions/${executionId}`,
        {
            params,
        },
    );
    return response.data;
}

export async function exportMarketingCampaignAudiencePreviewCsv(
    campaignId: string,
): Promise<CsvDownloadResult> {
    const response = await apiClient.get<Blob>(
        `/marketing/campaigns/${campaignId}/audience-preview/export`,
        {
            responseType: "blob",
        },
    );
    return {
        blob: response.data,
        filename: parseFilename(
            response.headers["content-disposition"],
            "campaign-audience-preview.csv",
        ),
        rowCount: Number(response.headers["x-supacrm-row-count"] ?? "0"),
    };
}

export async function exportMarketingCampaignExecutionResultsCsv(
    campaignId: string,
    executionId: string,
    params?: GetMarketingCampaignExecutionDetailParams,
): Promise<CsvDownloadResult> {
    const response = await apiClient.get<Blob>(
        `/marketing/campaigns/${campaignId}/executions/${executionId}/export`,
        {
            params,
            responseType: "blob",
        },
    );
    return {
        blob: response.data,
        filename: parseFilename(
            response.headers["content-disposition"],
            `campaign-execution-results-${executionId}.csv`,
        ),
        rowCount: Number(response.headers["x-supacrm-row-count"] ?? "0"),
    };
}

export async function createMarketingExecutionFollowUpHandoff(
    campaignId: string,
    executionId: string,
    payload: MarketingExecutionFollowUpHandoffRequest,
): Promise<MarketingExecutionFollowUpHandoffResponse> {
    const response = await apiClient.post<MarketingExecutionFollowUpHandoffResponse>(
        `/marketing/campaigns/${campaignId}/executions/${executionId}/follow-up-handoff`,
        payload,
    );
    return response.data;
}

export async function startMarketingCampaignEmailSend(
    campaignId: string,
): Promise<MarketingCampaignDetail> {
    const response = await apiClient.post<MarketingCampaignDetail>(
        `/marketing/campaigns/${campaignId}/send-email`,
    );
    return response.data;
}

export async function createWhatsAppLeadIntake(
    payload: WhatsAppLeadIntakeRequest,
): Promise<WhatsAppLeadIntakeResponse> {
    const response = await apiClient.post<WhatsAppLeadIntakeResponse>(
        "/marketing/whatsapp-intake",
        payload,
    );
    return response.data;
}

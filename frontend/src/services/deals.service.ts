import { apiClient } from "@/lib/api-client";
import type {
    Deal,
    DealCreateRequest,
    DealFollowUpUpdateRequest,
    DealListView,
    DealUpdateRequest,
    DealsListResponse,
    DeleteResponse,
    LeadImportRequest,
    LeadImportResult,
    LeadCreateRequest,
    PipelineReportResponse,
    SalesForecastReportResponse,
} from "@/types/crm";
import type { CsvDownloadResult } from "@/lib/download-file";

export interface GetDealsParams {
    view?: DealListView;
    q?: string;
    company_id?: string;
    contact_id?: string;
    product_id?: string;
    limit?: number;
    offset?: number;
}

function parseFilename(headerValue: string | undefined, fallback: string): string {
    if (!headerValue) {
        return fallback;
    }

    const match = headerValue.match(/filename="?([^"]+)"?/i);
    return match?.[1] ?? fallback;
}

export async function getDeals(
    params?: GetDealsParams,
): Promise<DealsListResponse> {
    const response = await apiClient.get<DealsListResponse>("/sales/deals", {
        params,
    });
    return response.data;
}

export async function getDealById(dealId: string): Promise<Deal> {
    const response = await apiClient.get<Deal>(`/sales/deals/${dealId}`);
    return response.data;
}

export async function createDeal(payload: DealCreateRequest): Promise<Deal> {
    const response = await apiClient.post<Deal>("/sales/deals", payload);
    return response.data;
}

export async function createLead(payload: LeadCreateRequest): Promise<Deal> {
    const response = await apiClient.post<Deal>("/sales/leads", payload);
    return response.data;
}

export async function updateDeal(
    dealId: string,
    payload: DealUpdateRequest,
): Promise<Deal> {
    const response = await apiClient.patch<Deal>(`/sales/deals/${dealId}`, payload);
    return response.data;
}

export async function updateDealFollowUp(
    dealId: string,
    payload: DealFollowUpUpdateRequest,
): Promise<Deal> {
    const response = await apiClient.patch<Deal>(`/sales/deals/${dealId}/follow-up`, payload);
    return response.data;
}

export async function deleteDeal(dealId: string): Promise<DeleteResponse> {
    const response = await apiClient.delete<DeleteResponse>(`/sales/deals/${dealId}`);
    return response.data;
}

export async function getPipelineReport(): Promise<PipelineReportResponse> {
    const response = await apiClient.get<PipelineReportResponse>("/sales/pipeline-report");
    return response.data;
}

export async function getSalesForecastReport(): Promise<SalesForecastReportResponse> {
    const response = await apiClient.get<SalesForecastReportResponse>("/sales/forecast-report");
    return response.data;
}

export async function importLeadsCsv(
    payload: LeadImportRequest,
): Promise<LeadImportResult> {
    const response = await apiClient.post<LeadImportResult>("/sales/leads/import", payload);
    return response.data;
}

export async function exportLeadsCsv(
    params?: Pick<GetDealsParams, "q" | "company_id" | "contact_id">,
): Promise<CsvDownloadResult> {
    const response = await apiClient.get<Blob>("/sales/leads/export", {
        params,
        responseType: "blob",
    });
    return {
        blob: response.data,
        filename: parseFilename(response.headers["content-disposition"], "leads-export.csv"),
        rowCount: Number(response.headers["x-supacrm-row-count"] ?? "0"),
    };
}

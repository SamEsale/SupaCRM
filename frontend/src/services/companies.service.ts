import { apiClient } from "@/lib/api-client";
import type {
    CompaniesListResponse,
    Company,
    CompanyCreateRequest,
} from "@/types/crm";

export async function getCompanies(): Promise<CompaniesListResponse> {
    const response = await apiClient.get<CompaniesListResponse>("/crm/companies");
    return response.data;
}

export async function createCompany(
    payload: CompanyCreateRequest,
): Promise<Company> {
    const response = await apiClient.post<Company>("/crm/companies", payload);
    return response.data;
}

import { apiClient } from "@/lib/api-client";
import type {
    CompaniesListResponse,
    Company,
    CompanyCreateRequest,
    CompanyUpdateRequest,
    DeleteResponse,
} from "@/types/crm";

export async function getCompanies(): Promise<CompaniesListResponse> {
    const response = await apiClient.get<CompaniesListResponse>("/crm/companies");
    return response.data;
}

export async function getCompanyById(companyId: string): Promise<Company> {
    const response = await apiClient.get<Company>(`/crm/companies/${companyId}`);
    return response.data;
}

export async function createCompany(
    payload: CompanyCreateRequest,
): Promise<Company> {
    const response = await apiClient.post<Company>("/crm/companies", payload);
    return response.data;
}

export async function updateCompany(
    companyId: string,
    payload: CompanyUpdateRequest,
): Promise<Company> {
    const response = await apiClient.patch<Company>(`/crm/companies/${companyId}`, payload);
    return response.data;
}

export async function deleteCompany(companyId: string): Promise<DeleteResponse> {
    const response = await apiClient.delete<DeleteResponse>(`/crm/companies/${companyId}`);
    return response.data;
}

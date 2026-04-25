import { apiClient } from "@/lib/api-client";
import type {
    Contact,
    ContactCreateRequest,
    ContactImportRequest,
    ContactImportResult,
    ContactUpdateRequest,
    ContactsListResponse,
    DeleteResponse,
} from "@/types/crm";

export interface GetContactsParams {
    q?: string;
    company_id?: string;
    limit?: number;
    offset?: number;
}

export interface CsvDownloadResult {
    blob: Blob;
    filename: string;
    rowCount: number;
}

function parseFilename(headerValue: string | undefined, fallback: string): string {
    if (!headerValue) {
        return fallback;
    }

    const match = headerValue.match(/filename="?([^"]+)"?/i);
    return match?.[1] ?? fallback;
}

export async function getContacts(
    params?: GetContactsParams,
): Promise<ContactsListResponse> {
    const response = await apiClient.get<ContactsListResponse>("/crm/contacts", {
        params,
    });
    return response.data;
}

export async function getContactById(contactId: string): Promise<Contact> {
    const response = await apiClient.get<Contact>(`/crm/contacts/${contactId}`);
    return response.data;
}

export async function createContact(
    payload: ContactCreateRequest,
): Promise<Contact> {
    const response = await apiClient.post<Contact>("/crm/contacts", payload);
    return response.data;
}

export async function updateContact(
    contactId: string,
    payload: ContactUpdateRequest,
): Promise<Contact> {
    const response = await apiClient.patch<Contact>(`/crm/contacts/${contactId}`, payload);
    return response.data;
}

export async function deleteContact(contactId: string): Promise<DeleteResponse> {
    const response = await apiClient.delete<DeleteResponse>(`/crm/contacts/${contactId}`);
    return response.data;
}

export async function importContactsCsv(
    payload: ContactImportRequest,
): Promise<ContactImportResult> {
    const response = await apiClient.post<ContactImportResult>("/crm/contacts/import", payload);
    return response.data;
}

export async function exportContactsCsv(
    params?: Pick<GetContactsParams, "q" | "company_id">,
): Promise<CsvDownloadResult> {
    const response = await apiClient.get<Blob>("/crm/contacts/export", {
        params,
        responseType: "blob",
    });
    return {
        blob: response.data,
        filename: parseFilename(response.headers["content-disposition"], "contacts-export.csv"),
        rowCount: Number(response.headers["x-supacrm-row-count"] ?? "0"),
    };
}

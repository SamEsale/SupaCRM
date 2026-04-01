import { apiClient } from "@/lib/api-client";
import type {
    Contact,
    ContactCreateRequest,
    ContactsListResponse,
} from "@/types/crm";

export async function getContacts(): Promise<ContactsListResponse> {
    const response = await apiClient.get<ContactsListResponse>("/crm/contacts");
    return response.data;
}

export async function createContact(
    payload: ContactCreateRequest,
): Promise<Contact> {
    const response = await apiClient.post<Contact>("/crm/contacts", payload);
    return response.data;
}

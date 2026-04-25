import { apiClient } from "@/lib/api-client";
import type {
    AccountingAccountListResponse,
    JournalEntryListResponse,
} from "@/types/accounting";

export interface GetJournalEntriesParams {
    source_type?: string;
    source_id?: string;
    source_event?: string;
    limit?: number;
    offset?: number;
}

export async function getAccountingAccounts(): Promise<AccountingAccountListResponse> {
    const response = await apiClient.get<AccountingAccountListResponse>("/accounting/accounts");
    return response.data;
}

export async function getJournalEntries(
    params?: GetJournalEntriesParams,
): Promise<JournalEntryListResponse> {
    const response = await apiClient.get<JournalEntryListResponse>("/accounting/journal-entries", {
        params,
    });
    return response.data;
}

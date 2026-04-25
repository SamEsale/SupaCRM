import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getAccountingAccounts: vi.fn(),
    getJournalEntries: vi.fn(),
    searchParams: new URLSearchParams({ source_type: "invoice", source_id: "invoice-1" }),
}));

vi.mock("next/navigation", () => ({
    useSearchParams: () => mocks.searchParams,
}));

vi.mock("@/services/accounting.service", () => ({
    getAccountingAccounts: mocks.getAccountingAccounts,
    getJournalEntries: mocks.getJournalEntries,
}));

import FinanceAccountingPage from "@/app/(dashboard)/finance/accounting/page";

describe("finance accounting page", () => {
    beforeEach(() => {
        mocks.getAccountingAccounts.mockReset();
        mocks.getJournalEntries.mockReset();
        mocks.searchParams = new URLSearchParams({ source_type: "invoice", source_id: "invoice-1" });

        mocks.getAccountingAccounts.mockResolvedValue({
            items: [
                {
                    id: "account-1",
                    tenant_id: "tenant-1",
                    code: "1000",
                    name: "Cash",
                    account_type: "asset",
                    system_key: "cash",
                    is_active: true,
                    created_at: "2026-04-13T10:00:00.000Z",
                    updated_at: "2026-04-13T10:00:00.000Z",
                },
                {
                    id: "account-2",
                    tenant_id: "tenant-1",
                    code: "1100",
                    name: "Accounts Receivable",
                    account_type: "asset",
                    system_key: "accounts_receivable",
                    is_active: true,
                    created_at: "2026-04-13T10:00:00.000Z",
                    updated_at: "2026-04-13T10:00:00.000Z",
                },
            ],
            total: 2,
        });
        mocks.getJournalEntries.mockResolvedValue({
            items: [
                {
                    id: "journal-1",
                    tenant_id: "tenant-1",
                    entry_date: "2026-04-12",
                    memo: "Invoice INV-000101 issued",
                    source_type: "invoice",
                    source_id: "invoice-1",
                    source_event: "invoice_issued",
                    currency: "USD",
                    total_debit: "1200.00",
                    total_credit: "1200.00",
                    created_at: "2026-04-12T10:00:00.000Z",
                    lines: [
                        {
                            id: "line-1",
                            tenant_id: "tenant-1",
                            journal_entry_id: "journal-1",
                            account_id: "account-2",
                            account_code: "1100",
                            account_name: "Accounts Receivable",
                            account_type: "asset",
                            line_order: 1,
                            description: "Recognize accounts receivable",
                            debit_amount: "1200.00",
                            credit_amount: "0.00",
                            created_at: "2026-04-12T10:00:00.000Z",
                        },
                    ],
                },
            ],
            total: 1,
        });
    });

    afterEach(() => cleanup());

    it("renders chart of accounts and filtered journal activity", async () => {
        render(<FinanceAccountingPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Accounting" })).toBeTruthy();
        });

        expect(mocks.getJournalEntries).toHaveBeenCalledWith({
            source_type: "invoice",
            source_id: "invoice-1",
            limit: 100,
            offset: 0,
        });
        expect(screen.getByText(/Filtered to/i)).toBeTruthy();
        expect(screen.getByText("1000")).toBeTruthy();
        expect(screen.getAllByText("Cash").length).toBeGreaterThan(0);
        expect(screen.getByText("Invoice INV-000101 issued")).toBeTruthy();
        expect(screen.getByText(/Recognize accounts receivable/i)).toBeTruthy();
    });
});

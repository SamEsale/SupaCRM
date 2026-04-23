import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getPayments: vi.fn(),
    getInvoices: vi.fn(),
    getCompanies: vi.fn(),
    searchParams: new URLSearchParams({ invoice_id: "invoice-1" }),
}));

vi.mock("next/navigation", () => ({
    useSearchParams: () => mocks.searchParams,
}));

vi.mock("@/services/payments.service", () => ({
    getPayments: mocks.getPayments,
}));

vi.mock("@/services/invoices.service", () => ({
    getInvoices: mocks.getInvoices,
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

import PaymentsPage from "@/app/(dashboard)/finance/payments/page";

describe("finance payments page", () => {
    beforeEach(() => {
        mocks.getPayments.mockReset();
        mocks.getInvoices.mockReset();
        mocks.getCompanies.mockReset();
        mocks.searchParams = new URLSearchParams({ invoice_id: "invoice-1" });

        mocks.getPayments.mockResolvedValue({
            items: [
                {
                    id: "payment-1",
                    tenant_id: "tenant-1",
                    invoice_id: "invoice-1",
                    amount: "300.00",
                    currency: "USD",
                    method: "bank_transfer",
                    status: "completed",
                    payment_date: "2026-04-13T09:30:00.000Z",
                    external_reference: "BT-100",
                    notes: "Deposit received",
                    created_at: "2026-04-13T09:30:00.000Z",
                    updated_at: "2026-04-13T09:30:00.000Z",
                },
                {
                    id: "payment-2",
                    tenant_id: "tenant-1",
                    invoice_id: "invoice-1",
                    amount: "200.00",
                    currency: "USD",
                    method: "cash",
                    status: "pending",
                    payment_date: "2026-04-14T11:00:00.000Z",
                    external_reference: null,
                    notes: null,
                    created_at: "2026-04-14T11:00:00.000Z",
                    updated_at: "2026-04-14T11:00:00.000Z",
                },
            ],
            total: 2,
        });
        mocks.getInvoices.mockResolvedValue({
            items: [
                {
                    id: "invoice-1",
                    tenant_id: "tenant-1",
                    number: "INV-000101",
                    company_id: "company-1",
                    contact_id: null,
                    product_id: null,
                    source_quote_id: "quote-1",
                    issue_date: "2026-04-13",
                    due_date: "2026-05-13",
                    currency: "USD",
                    total_amount: "1200.00",
                    status: "issued",
                    notes: null,
                    created_at: "2026-04-13T09:00:00.000Z",
                    updated_at: "2026-04-13T09:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.getCompanies.mockResolvedValue({
            items: [{ id: "company-1", tenant_id: "tenant-1", name: "Northwind" }],
            total: 1,
        });
    });

    afterEach(() => cleanup());

    it("renders payment records and applies the invoice filter from the URL", async () => {
        render(<PaymentsPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Payments" })).toBeTruthy();
        });

        expect(mocks.getPayments).toHaveBeenCalledWith(
            expect.objectContaining({
                invoice_id: "invoice-1",
                limit: 100,
                offset: 0,
            }),
        );
        expect(screen.getByText(/Filtered to invoice invoice-1/i)).toBeTruthy();
        expect(screen.getByText(/1 completed payments\./i)).toBeTruthy();
        expect(screen.getByText(/Saved but not completed\./i)).toBeTruthy();
        expect(screen.getAllByRole("link", { name: "INV-000101" })).toHaveLength(2);
        expect(screen.getAllByText(/Northwind/i)).toHaveLength(2);
        expect(screen.getByText(/Deposit received/i)).toBeTruthy();

        fireEvent.change(screen.getByDisplayValue("All statuses"), {
            target: { value: "pending" },
        });

        await waitFor(() => {
            expect(mocks.getPayments).toHaveBeenLastCalledWith(
                expect.objectContaining({
                    invoice_id: "invoice-1",
                    status: "pending",
                    limit: 100,
                    offset: 0,
                }),
            );
        });
    });
});

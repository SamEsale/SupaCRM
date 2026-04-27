import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import axios from "axios";

const mocks = vi.hoisted(() => ({
    authState: {
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    },
    getCurrentTenant: vi.fn(),
    getRevenueFlowReport: vi.fn(),
    getQuotes: vi.fn(),
    getInvoices: vi.fn(),
    getExpenses: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => mocks.authState,
}));

vi.mock("@/services/reporting.service", () => ({
    getRevenueFlowReport: mocks.getRevenueFlowReport,
}));

vi.mock("@/services/tenants.service", () => ({
    getCurrentTenant: mocks.getCurrentTenant,
}));

vi.mock("@/services/quotes.service", () => ({
    getQuotes: mocks.getQuotes,
}));

vi.mock("@/services/invoices.service", () => ({
    getInvoices: mocks.getInvoices,
}));

vi.mock("@/services/expenses.service", () => ({
    getExpenses: mocks.getExpenses,
}));

import FinancePage from "@/app/(dashboard)/finance/page";

describe("finance overview page", () => {
    beforeEach(() => {
        mocks.authState.isReady = true;
        mocks.authState.isAuthenticated = true;
        mocks.authState.accessToken = "token";
        mocks.getRevenueFlowReport.mockReset();
        mocks.getQuotes.mockReset();
        mocks.getInvoices.mockReset();
        mocks.getCurrentTenant.mockReset();
        mocks.getExpenses.mockReset();

        mocks.getCurrentTenant.mockResolvedValue({
            id: "tenant-1",
            name: "Northwind Workspace",
            is_active: true,
            status: "active",
            status_reason: null,
            default_currency: "SEK",
            secondary_currency: "EUR",
            secondary_currency_rate: "0.091500",
            secondary_currency_rate_source: "operator_manual",
            secondary_currency_rate_as_of: "2026-04-12T09:00:00.000Z",
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-12T10:00:00.000Z",
        });

        mocks.getRevenueFlowReport.mockResolvedValue({
            sales_summary: {
                total_open_pipeline_amount: "2400.00",
                weighted_pipeline_amount: "1200.00",
                won_amount: "900.00",
                lost_amount: "250.00",
                deals_won_this_period_count: 1,
                deals_won_this_period_amount: "900.00",
                deals_lost_this_period_count: 1,
                deals_lost_this_period_amount: "250.00",
                overdue_follow_up_count: 0,
                due_today_follow_up_count: 1,
                upcoming_follow_up_count: 2,
                currencies: ["USD", "EUR"],
                report_period_start: "2026-03-13T10:00:00.000Z",
                report_period_end: "2026-04-12T10:00:00.000Z",
                generated_at: "2026-04-12T10:00:00.000Z",
            },
            summary: {
                quote_count: 3,
                quote_created_this_period_count: 2,
                invoice_count: 2,
                invoice_created_this_period_count: 2,
                invoice_issued_count: 1,
                invoice_paid_count: 1,
                invoice_overdue_count: 0,
                quote_currencies: ["USD"],
                invoice_currencies: ["USD", "EUR"],
                report_period_start: "2026-03-13T10:00:00.000Z",
                report_period_end: "2026-04-12T10:00:00.000Z",
                generated_at: "2026-04-12T10:00:00.000Z",
            },
            quote_status_breakdown: [
                { status: "accepted", count: 1, total_amount: "1200.00", currencies: ["USD"] },
                { status: "draft", count: 2, total_amount: "800.00", currencies: ["USD"] },
            ],
            invoice_status_breakdown: [
                { status: "issued", count: 1, total_amount: "1200.00", currencies: ["USD"] },
                { status: "paid", count: 1, total_amount: "900.00", currencies: ["EUR"] },
            ],
        });
        mocks.getQuotes.mockResolvedValue({
            items: [{ id: "quote-1", number: "QTE-000101", status: "accepted", total_amount: "1200.00", currency: "USD" }],
            total: 1,
        });
        mocks.getInvoices.mockResolvedValue({
            items: [{ id: "invoice-1", number: "INV-000101", status: "issued", total_amount: "1200.00", currency: "USD" }],
            total: 1,
        });
        mocks.getExpenses.mockResolvedValue({
            items: [
                {
                    id: "expense-1",
                    tenant_id: "tenant-1",
                    title: "Meta ads",
                    description: "Launch spend",
                    amount: "120.00",
                    currency: "SEK",
                    expense_date: "2026-04-11",
                    category: "marketing",
                    status: "approved",
                    vendor_name: "Meta",
                    created_at: "2026-04-12T10:00:00.000Z",
                    updated_at: "2026-04-12T10:00:00.000Z",
                },
            ],
            total: 1,
        });
    });

    afterEach(() => cleanup());

    it("does not call protected finance overview loaders before auth readiness", async () => {
        mocks.authState.isReady = false;

        const view = render(<FinancePage />);

        await waitFor(() => {
            expect(mocks.getCurrentTenant).not.toHaveBeenCalled();
            expect(mocks.getRevenueFlowReport).not.toHaveBeenCalled();
            expect(mocks.getQuotes).not.toHaveBeenCalled();
            expect(mocks.getInvoices).not.toHaveBeenCalled();
            expect(mocks.getExpenses).not.toHaveBeenCalled();
        });

        mocks.authState.isReady = true;
        view.rerender(<FinancePage />);

        await waitFor(() => {
            expect(mocks.getCurrentTenant).toHaveBeenCalledTimes(1);
            expect(mocks.getRevenueFlowReport).toHaveBeenCalledTimes(1);
            expect(mocks.getQuotes).toHaveBeenCalledTimes(1);
            expect(mocks.getInvoices).toHaveBeenCalledTimes(1);
            expect(mocks.getExpenses).toHaveBeenCalledTimes(1);
        });
    });

    it("renders the commercial flow overview and warns honestly about mixed currencies", async () => {
        render(<FinancePage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Finance" })).toBeTruthy();
        });

        expect(screen.getByText(/Revenue totals span multiple currencies/i)).toBeTruthy();
        expect(screen.getByRole("link", { name: "Expenses" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Recent Expenses" })).toBeTruthy();
        expect(screen.getByText(/Secondary currency view uses a saved manual rate/i)).toBeTruthy();
        expect(screen.getByText(/Meta ads/i)).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Quote Status Breakdown" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Invoice Status Breakdown" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "QTE-000101" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "INV-000101" })).toBeTruthy();
    });

    it("keeps the overview available when tenant metadata is blocked by admin-only access", async () => {
        mocks.getCurrentTenant.mockRejectedValueOnce(
            new axios.AxiosError(
                "Request failed with status code 403",
                "ERR_BAD_REQUEST",
                undefined,
                undefined,
                {
                    data: { detail: "Forbidden" },
                    status: 403,
                    statusText: "Forbidden",
                    headers: {},
                    config: { headers: {} as never },
                },
            ),
        );

        render(<FinancePage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Finance" })).toBeTruthy();
        });

        expect(screen.queryByText(/Failed to load finance overview/i)).toBeNull();
        expect(screen.getByRole("heading", { name: "Recent Expenses" })).toBeTruthy();
        expect(screen.queryByText(/Secondary currency view uses a saved manual rate/i)).toBeNull();
        expect(mocks.getRevenueFlowReport).toHaveBeenCalledTimes(1);
        expect(mocks.getQuotes).toHaveBeenCalledTimes(1);
        expect(mocks.getInvoices).toHaveBeenCalledTimes(1);
        expect(mocks.getExpenses).toHaveBeenCalledTimes(1);
    });
});

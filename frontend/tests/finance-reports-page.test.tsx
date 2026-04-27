import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getFinanceReportsSnapshot: vi.fn(),
}));

vi.mock("@/services/reporting.service", async () => {
    const actual = await vi.importActual<typeof import("@/services/reporting.service")>("@/services/reporting.service");
    return {
        ...actual,
        getFinanceReportsSnapshot: mocks.getFinanceReportsSnapshot,
    };
});

import FinanceReportsPage from "@/app/(dashboard)/reports/finance/page";

describe("finance reports page", () => {
    beforeEach(() => {
        mocks.getFinanceReportsSnapshot.mockReset();
        mocks.getFinanceReportsSnapshot.mockResolvedValue({
            revenue_flow: {
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
                    currencies: ["USD"],
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
                    invoice_currencies: ["USD"],
                    report_period_start: "2026-03-13T10:00:00.000Z",
                    report_period_end: "2026-04-12T10:00:00.000Z",
                    generated_at: "2026-04-12T10:00:00.000Z",
                },
                quote_status_breakdown: [],
                invoice_status_breakdown: [],
            },
            financial_statements: {
                profit_and_loss: {
                    revenue_lines: [
                        {
                            account_id: "account-3",
                            code: "4000",
                            name: "Sales Revenue",
                            account_type: "revenue",
                            total_amount: "1200.00",
                            currencies: ["USD"],
                        },
                    ],
                    expense_lines: [],
                    total_revenue: "1200.00",
                    total_expenses: "0.00",
                    net_income: "1200.00",
                    currencies: ["USD"],
                },
                balance_sheet: {
                    asset_lines: [
                        {
                            account_id: "account-2",
                            code: "1100",
                            name: "Accounts Receivable",
                            account_type: "asset",
                            total_amount: "1200.00",
                            currencies: ["USD"],
                        },
                    ],
                    liability_lines: [],
                    equity_lines: [
                        {
                            account_id: "current_earnings",
                            code: "CURR-EARN",
                            name: "Current Earnings",
                            account_type: "equity",
                            total_amount: "1200.00",
                            currencies: ["USD"],
                        },
                    ],
                    total_assets: "1200.00",
                    total_liabilities: "0.00",
                    total_equity: "1200.00",
                    total_liabilities_and_equity: "1200.00",
                    currencies: ["USD"],
                },
                receivables: {
                    open_receivables_amount: "1200.00",
                    issued_invoice_count: 1,
                    overdue_invoice_count: 0,
                    paid_invoice_count: 1,
                    currencies: ["USD"],
                    items: [
                        {
                            invoice_id: "invoice-1",
                            invoice_number: "INV-000101",
                            company_id: "company-1",
                            status: "issued",
                            due_date: "2026-04-30",
                            currency: "USD",
                            total_amount: "1200.00",
                            paid_amount: "300.00",
                            outstanding_amount: "900.00",
                        },
                    ],
                },
                vat_supported: false,
                vat_note: "VAT summary is not yet available because invoices do not currently persist tax rates or line-level tax amounts.",
                generated_at: "2026-04-13T10:00:00.000Z",
            },
            payments_summary: {
                payment_count: 2,
                completed_payment_count: 1,
                completed_payment_amount: "300.00",
                pending_payment_count: 1,
                failed_payment_count: 0,
                cancelled_payment_count: 0,
                payment_currencies: ["USD"],
                generated_at: "2026-04-13T10:00:00.000Z",
            },
            payment_status_breakdown: [
                {
                    status: "completed",
                    count: 1,
                    total_amount: "300.00",
                    currencies: ["USD"],
                },
                {
                    status: "pending",
                    count: 1,
                    total_amount: "200.00",
                    currencies: ["USD"],
                },
            ],
        });
    });

    afterEach(() => cleanup());

    it("renders profit and loss, balance sheet, and receivables visibility", async () => {
        render(<FinanceReportsPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Finance Reports" })).toBeTruthy();
        });

        expect(screen.getByRole("heading", { name: "Profit & Loss" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Balance Sheet" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Receivables" })).toBeTruthy();
        expect(screen.getByText(/4000 .* Sales Revenue/i)).toBeTruthy();
        expect(screen.getByText(/1100 .* Accounts Receivable/i)).toBeTruthy();
        expect(screen.getByRole("link", { name: "INV-000101" })).toBeTruthy();
        expect(screen.getByText(/Completed payments/i)).toBeTruthy();
        expect(screen.getByText(/Paid .* outstanding/i)).toBeTruthy();
        expect(screen.getByText(/VAT summary is not yet available/i)).toBeTruthy();
    });
});

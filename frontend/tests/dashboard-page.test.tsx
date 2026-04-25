import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getDeals: vi.fn(),
    getSalesForecastReport: vi.fn(),
    getSupportSummary: vi.fn(),
    getFinanceReportsSnapshot: vi.fn(),
    getMarketingCampaigns: vi.fn(),
    getRecentAuditActivity: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
}));

vi.mock("@/services/deals.service", () => ({
    getDeals: mocks.getDeals,
    getSalesForecastReport: mocks.getSalesForecastReport,
}));

vi.mock("@/services/support.service", () => ({
    getSupportSummary: mocks.getSupportSummary,
}));

vi.mock("@/services/reporting.service", () => ({
    getFinanceReportsSnapshot: mocks.getFinanceReportsSnapshot,
}));

vi.mock("@/services/marketing.service", () => ({
    getMarketingCampaigns: mocks.getMarketingCampaigns,
}));

vi.mock("@/services/audit.service", () => ({
    getRecentAuditActivity: mocks.getRecentAuditActivity,
}));

import DashboardPage from "@/app/(dashboard)/dashboard/page";

describe("dashboard page", () => {
    beforeEach(() => {
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getDeals.mockReset();
        mocks.getSalesForecastReport.mockReset();
        mocks.getSupportSummary.mockReset();
        mocks.getFinanceReportsSnapshot.mockReset();
        mocks.getMarketingCampaigns.mockReset();
        mocks.getRecentAuditActivity.mockReset();

        mocks.getCompanies.mockResolvedValue({
            items: [],
            total: 24,
        });
        mocks.getContacts.mockResolvedValue({
            items: [],
            total: 120,
        });
        mocks.getDeals.mockResolvedValue({
            items: [],
            total: 9,
        });
        mocks.getSalesForecastReport.mockResolvedValue({
            summary: {
                total_open_pipeline_amount: "5000.00",
                weighted_pipeline_amount: "3200.00",
                won_amount: "1800.00",
                lost_amount: "200.00",
                deals_won_this_period_count: 2,
                deals_won_this_period_amount: "1800.00",
                deals_lost_this_period_count: 1,
                deals_lost_this_period_amount: "200.00",
                overdue_follow_up_count: 3,
                due_today_follow_up_count: 1,
                upcoming_follow_up_count: 4,
                currencies: ["USD"],
                report_period_start: "2026-04-01T00:00:00.000Z",
                report_period_end: "2026-05-01T00:00:00.000Z",
                generated_at: "2026-04-13T10:00:00.000Z",
            },
            stage_breakdown: [],
            opportunity_stage_breakdown: [],
        });
        mocks.getSupportSummary.mockResolvedValue({
            open_count: 4,
            in_progress_count: 2,
            urgent_count: 1,
            resolved_this_period_count: 3,
            report_period_start: "2026-04-01T00:00:00.000Z",
            report_period_end: "2026-05-01T00:00:00.000Z",
            generated_at: "2026-04-13T10:00:00.000Z",
        });
        mocks.getFinanceReportsSnapshot.mockResolvedValue({
            revenue_flow: {
                sales_summary: {
                    total_open_pipeline_amount: "5000.00",
                    weighted_pipeline_amount: "3200.00",
                    won_amount: "1800.00",
                    lost_amount: "200.00",
                    deals_won_this_period_count: 2,
                    deals_won_this_period_amount: "1800.00",
                    deals_lost_this_period_count: 1,
                    deals_lost_this_period_amount: "200.00",
                    overdue_follow_up_count: 3,
                    due_today_follow_up_count: 1,
                    upcoming_follow_up_count: 4,
                    currencies: ["USD"],
                    report_period_start: "2026-04-01T00:00:00.000Z",
                    report_period_end: "2026-05-01T00:00:00.000Z",
                    generated_at: "2026-04-13T10:00:00.000Z",
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
                    report_period_start: "2026-04-01T00:00:00.000Z",
                    report_period_end: "2026-05-01T00:00:00.000Z",
                    generated_at: "2026-04-13T10:00:00.000Z",
                },
                quote_status_breakdown: [],
                invoice_status_breakdown: [],
            },
            financial_statements: {
                profit_and_loss: {
                    revenue_lines: [],
                    expense_lines: [],
                    total_revenue: "1250.00",
                    total_expenses: "0.00",
                    net_income: "1250.00",
                    currencies: ["USD"],
                },
                balance_sheet: {
                    asset_lines: [],
                    liability_lines: [],
                    equity_lines: [],
                    total_assets: "1250.00",
                    total_liabilities: "0.00",
                    total_equity: "1250.00",
                    total_liabilities_and_equity: "1250.00",
                    currencies: ["USD"],
                },
                receivables: {
                    open_receivables_amount: "750.00",
                    issued_invoice_count: 2,
                    overdue_invoice_count: 1,
                    paid_invoice_count: 1,
                    currencies: ["USD"],
                    items: [],
                },
                vat_supported: false,
                vat_note: "VAT reporting is not supported in this launch slice.",
                generated_at: "2026-04-13T10:00:00.000Z",
            },
            payments_summary: {
                payment_count: 3,
                completed_payment_count: 2,
                completed_payment_amount: "1250.00",
                pending_payment_count: 1,
                failed_payment_count: 0,
                cancelled_payment_count: 0,
                payment_currencies: ["USD"],
                generated_at: "2026-04-13T10:00:00.000Z",
            },
            payment_status_breakdown: [],
        });
        mocks.getMarketingCampaigns.mockResolvedValue({
            items: [],
            total: 5,
        });
        mocks.getRecentAuditActivity.mockResolvedValue({
            items: [
                {
                    id: "audit-1",
                    action: "sales.deal.create",
                    resource: "deal",
                    resource_id: "deal-1",
                    status_code: 200,
                    message: "Created deal Acceptance Deal",
                    actor_user_id: "user-1",
                    actor_full_name: "Alex Admin",
                    actor_email: "alex@example.com",
                    created_at: "2026-04-13T10:30:00.000Z",
                },
            ],
            total: 1,
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders useful dashboard KPIs and recent activity from real module data", async () => {
        render(<DashboardPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
        });

        expect(screen.getByRole("heading", { name: "KPIs" })).toBeTruthy();
        expect(screen.getByText("Contacts")).toBeTruthy();
        expect(screen.getByText("120")).toBeTruthy();
        expect(screen.getByText("Tracked Deals")).toBeTruthy();
        expect(screen.getByText("$3,200.00")).toBeTruthy();
        expect(screen.getByText("Support Queue")).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Activity Feed" })).toBeTruthy();
        expect(screen.getByText("Created deal Acceptance Deal")).toBeTruthy();
        expect(screen.getByText("Alex Admin")).toBeTruthy();
    });

    it("keeps the dashboard usable when some module widgets are unavailable", async () => {
        mocks.getFinanceReportsSnapshot.mockRejectedValueOnce({
            response: {
                status: 403,
                data: {
                    error: {
                        code: "forbidden",
                        message: "You do not have permission to perform this action.",
                    },
                },
            },
        });
        mocks.getMarketingCampaigns.mockRejectedValueOnce(new Error("Marketing offline"));
        mocks.getRecentAuditActivity.mockResolvedValueOnce({
            items: [],
            total: 0,
        });

        render(<DashboardPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
        });

        expect(screen.getByText("Partial dashboard access")).toBeTruthy();
        expect(screen.getByText("Finance reporting widgets are hidden for this account.")).toBeTruthy();
        expect(screen.getByText("Marketing offline")).toBeTruthy();
        expect(screen.getByText("No recent activity has been recorded for this tenant yet.")).toBeTruthy();
        expect(screen.getByText("Contacts")).toBeTruthy();
    });
});

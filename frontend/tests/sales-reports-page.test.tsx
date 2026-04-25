import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getSalesForecastReport: vi.fn(),
    getDeals: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
}));

vi.mock("@/services/deals.service", () => ({
    getSalesForecastReport: mocks.getSalesForecastReport,
    getDeals: mocks.getDeals,
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
}));

import SalesReportsPage from "@/app/(dashboard)/reports/sales/page";

describe("sales reports page", () => {
    beforeEach(() => {
        mocks.getSalesForecastReport.mockReset();
        mocks.getDeals.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();

        mocks.getSalesForecastReport.mockResolvedValue({
            summary: {
                total_open_pipeline_amount: "12000.00",
                weighted_pipeline_amount: "6100.00",
                won_amount: "8400.00",
                lost_amount: "2200.00",
                deals_won_this_period_count: 2,
                deals_won_this_period_amount: "5400.00",
                deals_lost_this_period_count: 1,
                deals_lost_this_period_amount: "1200.00",
                overdue_follow_up_count: 1,
                due_today_follow_up_count: 1,
                upcoming_follow_up_count: 2,
                currencies: ["USD"],
                report_period_start: "2026-04-01T00:00:00.000Z",
                report_period_end: "2026-05-01T00:00:00.000Z",
                generated_at: "2026-04-12T11:00:00.000Z",
            },
            stage_breakdown: [
                { stage: "new lead", count: 1, open_amount: "1000.00", weighted_amount: "100.00" },
                { stage: "qualified lead", count: 2, open_amount: "5000.00", weighted_amount: "1250.00" },
                { stage: "proposal sent", count: 1, open_amount: "3000.00", weighted_amount: "1500.00" },
                { stage: "estimate sent", count: 1, open_amount: "3000.00", weighted_amount: "1800.00" },
                { stage: "negotiating contract terms", count: 1, open_amount: "0.00", weighted_amount: "0.00" },
                { stage: "contract signed", count: 2, open_amount: "0.00", weighted_amount: "0.00" },
                { stage: "deal not secured", count: 1, open_amount: "0.00", weighted_amount: "0.00" },
            ],
            opportunity_stage_breakdown: [
                { stage: "qualified lead", count: 2, open_amount: "5000.00", weighted_amount: "1250.00" },
                { stage: "proposal sent", count: 1, open_amount: "3000.00", weighted_amount: "1500.00" },
                { stage: "estimate sent", count: 1, open_amount: "3000.00", weighted_amount: "1800.00" },
                { stage: "negotiating contract terms", count: 0, open_amount: "0.00", weighted_amount: "0.00" },
            ],
        });
        mocks.getDeals
            .mockResolvedValueOnce({
                items: [
                    {
                        id: "deal-1",
                        tenant_id: "tenant-1",
                        name: "Website expansion",
                        company_id: "company-1",
                        contact_id: "contact-1",
                        product_id: null,
                        amount: "1200.00",
                        currency: "USD",
                        stage: "qualified lead",
                        status: "in progress",
                        expected_close_date: null,
                        notes: null,
                        next_follow_up_at: "2026-04-10T09:00:00.000Z",
                        follow_up_note: "Call back finance",
                        closed_at: null,
                        created_at: "2026-04-01T10:00:00.000Z",
                        updated_at: "2026-04-10T10:00:00.000Z",
                    },
                ],
                total: 1,
            })
            .mockResolvedValueOnce({
                items: [
                    {
                        id: "deal-2",
                        tenant_id: "tenant-1",
                        name: "Renewal package",
                        company_id: "company-1",
                        contact_id: "contact-1",
                        product_id: null,
                        amount: "4500.00",
                        currency: "USD",
                        stage: "qualified lead",
                        status: "open",
                        expected_close_date: null,
                        notes: null,
                        next_follow_up_at: null,
                        follow_up_note: null,
                        closed_at: null,
                        created_at: "2026-04-02T10:00:00.000Z",
                        updated_at: "2026-04-10T10:00:00.000Z",
                    },
                ],
                total: 1,
            });
        mocks.getCompanies.mockResolvedValue({
            items: [
                {
                    id: "company-1",
                    tenant_id: "tenant-1",
                    name: "Northwind Labs",
                    website: null,
                    email: null,
                    phone: null,
                    industry: null,
                    address: null,
                    vat_number: null,
                    registration_number: null,
                    notes: null,
                    created_at: "2026-04-01T10:00:00.000Z",
                    updated_at: "2026-04-01T10:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.getContacts.mockResolvedValue({
            items: [
                {
                    id: "contact-1",
                    tenant_id: "tenant-1",
                    first_name: "Alex",
                    last_name: "Admin",
                    email: "alex@example.com",
                    phone: null,
                    company_id: "company-1",
                    company: "Northwind Labs",
                    job_title: null,
                    notes: null,
                    created_at: "2026-04-01T10:00:00.000Z",
                    updated_at: "2026-04-01T10:00:00.000Z",
                },
            ],
            total: 1,
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders weighted forecasting, stage breakdowns, and attention lists", async () => {
        render(<SalesReportsPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Sales Reports" })).toBeTruthy();
        });

        expect(mocks.getSalesForecastReport).toHaveBeenCalled();
        expect(mocks.getDeals).toHaveBeenNthCalledWith(1, { limit: 200, offset: 0 });
        expect(mocks.getDeals).toHaveBeenNthCalledWith(2, { view: "opportunities", limit: 200, offset: 0 });
        expect(screen.getByText("$12,000.00")).toBeTruthy();
        expect(screen.getByText("$6,100.00")).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Pipeline by stage" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Overdue follow-ups" })).toBeTruthy();
        expect(screen.getByText("Website expansion")).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Opportunities requiring attention" })).toBeTruthy();
        expect(screen.getByText("Renewal package")).toBeTruthy();
        expect(screen.getByText(/No follow-up scheduled/i)).toBeTruthy();
    });
});

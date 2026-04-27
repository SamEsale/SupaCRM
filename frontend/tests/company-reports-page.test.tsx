import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getCompanyReportsSnapshot: vi.fn(),
}));

vi.mock("@/services/reporting.service", async () => {
    const actual = await vi.importActual<typeof import("@/services/reporting.service")>("@/services/reporting.service");
    return {
        ...actual,
        getCompanyReportsSnapshot: mocks.getCompanyReportsSnapshot,
    };
});

import CompanyReportsPage from "@/app/(dashboard)/reports/companies/page";

describe("company reports page", () => {
    beforeEach(() => {
        mocks.getCompanyReportsSnapshot.mockReset();
        mocks.getCompanyReportsSnapshot.mockResolvedValue({
            summary: {
                total_companies: 5,
                companies_created_this_period_count: 2,
                companies_with_open_deals_count: 2,
                companies_with_won_deals_count: 1,
                companies_with_contacts_count: 3,
                companies_without_contacts_count: 2,
                companies_with_invoices_count: 2,
                companies_with_support_tickets_count: 1,
                report_period_start: "2026-04-01T00:00:00.000Z",
                report_period_end: "2026-05-01T00:00:00.000Z",
                generated_at: "2026-04-14T10:00:00.000Z",
            },
            contact_breakdown: [
                { company_id: "company-1", company_name: "Northwind", contact_count: 4 },
            ],
            recent_companies: [
                {
                    company_id: "company-1",
                    company_name: "Northwind",
                    updated_at: "2026-04-14T08:00:00.000Z",
                    contact_count: 4,
                    open_deals_count: 2,
                    won_deals_count: 1,
                    invoice_count: 2,
                    support_ticket_count: 1,
                },
            ],
        });
    });

    afterEach(() => cleanup());

    it("renders company report summary cards and recent companies", async () => {
        render(<CompanyReportsPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Company Reports" })).toBeTruthy();
        });

        expect(screen.getByRole("heading", { name: "Companies by contact coverage" })).toBeTruthy();
        expect(screen.getAllByText("Northwind").length).toBeGreaterThan(0);
        expect(screen.getByRole("heading", { name: "Most recently updated companies" })).toBeTruthy();
        expect(screen.getByText(/Support tickets linked: 1/i)).toBeTruthy();
        expect(screen.getByRole("link", { name: "Add Company" })).toBeTruthy();
    });
});

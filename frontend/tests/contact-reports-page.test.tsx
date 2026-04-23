import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getContactReportsSnapshot: vi.fn(),
}));

vi.mock("@/services/reporting.service", async () => {
    const actual = await vi.importActual<typeof import("@/services/reporting.service")>("@/services/reporting.service");
    return {
        ...actual,
        getContactReportsSnapshot: mocks.getContactReportsSnapshot,
    };
});

import ContactReportsPage from "@/app/(dashboard)/reports/contacts/page";

describe("contact reports page", () => {
    beforeEach(() => {
        mocks.getContactReportsSnapshot.mockReset();
        mocks.getContactReportsSnapshot.mockResolvedValue({
            summary: {
                total_contacts: 12,
                contacts_created_this_period_count: 4,
                contacts_with_open_deals_count: 3,
                contacts_with_won_deals_count: 2,
                contacts_without_company_count: 1,
                contacts_with_support_tickets_count: 5,
                report_period_start: "2026-04-01T00:00:00.000Z",
                report_period_end: "2026-05-01T00:00:00.000Z",
                generated_at: "2026-04-14T10:00:00.000Z",
            },
            contacts_by_company: [
                { company_id: "company-1", company_name: "Northwind", contact_count: 6 },
                { company_id: null, company_name: "No company", contact_count: 1 },
            ],
            recent_contacts: [
                {
                    contact_id: "contact-1",
                    full_name: "Alicia Admin",
                    company_id: "company-1",
                    company_name: "Northwind",
                    email: "alicia@example.com",
                    phone: "+46-555-01",
                    updated_at: "2026-04-14T09:00:00.000Z",
                    open_deals_count: 1,
                    won_deals_count: 1,
                    support_ticket_count: 2,
                },
            ],
        });
    });

    afterEach(() => cleanup());

    it("renders contact report summary cards, breakdowns, and recent contacts", async () => {
        render(<ContactReportsPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Contact Reports" })).toBeTruthy();
        });

        expect(screen.getByText("12")).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Contacts by company" })).toBeTruthy();
        expect(screen.getAllByText("Northwind").length).toBeGreaterThan(0);
        expect(screen.getByRole("heading", { name: "Most recently updated contacts" })).toBeTruthy();
        expect(screen.getByText("Alicia Admin")).toBeTruthy();
        expect(screen.getByText(/Support tickets: 2/i)).toBeTruthy();
        expect(screen.getByRole("link", { name: "Add Lead" })).toBeTruthy();
    });
});

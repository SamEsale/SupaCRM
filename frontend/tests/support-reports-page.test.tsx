import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getSupportReportsSnapshot: vi.fn(),
}));

vi.mock("@/services/reporting.service", async () => {
    const actual = await vi.importActual<typeof import("@/services/reporting.service")>("@/services/reporting.service");
    return {
        ...actual,
        getSupportReportsSnapshot: mocks.getSupportReportsSnapshot,
    };
});

import SupportReportsPage from "@/app/(dashboard)/reports/support/page";

describe("support reports page", () => {
    beforeEach(() => {
        mocks.getSupportReportsSnapshot.mockReset();
        mocks.getSupportReportsSnapshot.mockResolvedValue({
            summary: {
                total_tickets: 8,
                open_tickets: 2,
                in_progress_tickets: 2,
                waiting_on_customer_tickets: 1,
                resolved_tickets: 2,
                closed_tickets: 1,
                urgent_active_tickets: 1,
                tickets_linked_to_deals_count: 3,
                tickets_linked_to_invoices_count: 2,
                report_period_start: "2026-04-01T00:00:00.000Z",
                report_period_end: "2026-05-01T00:00:00.000Z",
                generated_at: "2026-04-14T10:00:00.000Z",
            },
            tickets_by_priority: [
                { label: "urgent", count: 1 },
                { label: "high", count: 3 },
            ],
            tickets_by_source: [
                { label: "email", count: 4 },
                { label: "manual", count: 2 },
            ],
            tickets_by_company: [
                { company_id: "company-1", company_name: "Northwind", ticket_count: 5 },
            ],
            recent_tickets: [
                {
                    ticket_id: "ticket-1",
                    title: "Invoice correction",
                    status: "open",
                    priority: "urgent",
                    source: "email",
                    company_id: "company-1",
                    company_name: "Northwind",
                    contact_id: "contact-1",
                    related_deal_id: "deal-1",
                    related_invoice_id: "invoice-1",
                    updated_at: "2026-04-14T10:30:00.000Z",
                },
            ],
        });
    });

    afterEach(() => cleanup());

    it("renders support status summaries, breakdowns, and recent tickets", async () => {
        render(<SupportReportsPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Support Reports" })).toBeTruthy();
        });

        expect(screen.getByRole("heading", { name: "Tickets by priority" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Tickets by source" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Tickets by company" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Recently updated tickets" })).toBeTruthy();
        expect(screen.getByText("Invoice correction")).toBeTruthy();
        expect(screen.getByText(/Deal linked/i)).toBeTruthy();
        expect(screen.getByRole("link", { name: "Create Ticket" })).toBeTruthy();
    });
});

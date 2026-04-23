import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getSupportTickets: vi.fn(),
    getSupportSummary: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("@/services/support.service", () => ({
    getSupportTickets: mocks.getSupportTickets,
    getSupportSummary: mocks.getSupportSummary,
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
}));

import SupportPage from "@/app/(dashboard)/support/page";

describe("support list page", () => {
    beforeEach(() => {
        mocks.getSupportTickets.mockReset();
        mocks.getSupportSummary.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();

        mocks.getSupportTickets.mockResolvedValue({
            items: [
                {
                    id: "ticket-1",
                    tenant_id: "tenant-1",
                    title: "Customer billing issue",
                    description: "Needs invoice correction",
                    status: "open",
                    priority: "urgent",
                    source: "email",
                    company_id: "company-1",
                    company_name: "Northwind",
                    contact_id: "contact-1",
                    contact_name: "Alicia Andersson",
                    assigned_to_user_id: "user-1",
                    assigned_to_full_name: "Support Agent",
                    assigned_to_email: "agent@example.com",
                    related_deal_id: "deal-1",
                    related_deal_name: "Renewal deal",
                    related_invoice_id: "invoice-1",
                    related_invoice_number: "INV-1001",
                    created_at: "2026-04-12T08:00:00.000Z",
                    updated_at: "2026-04-12T09:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.getSupportSummary.mockResolvedValue({
            open_count: 4,
            in_progress_count: 2,
            urgent_count: 1,
            resolved_this_period_count: 3,
            report_period_start: "2026-04-01T00:00:00.000Z",
            report_period_end: "2026-05-01T00:00:00.000Z",
            generated_at: "2026-04-12T09:00:00.000Z",
        });
        mocks.getCompanies.mockResolvedValue({
            items: [
                {
                    id: "company-1",
                    tenant_id: "tenant-1",
                    name: "Northwind",
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
                    first_name: "Alicia",
                    last_name: "Andersson",
                    email: "alicia@example.com",
                    phone: "+46700000000",
                    company_id: "company-1",
                    company: "Northwind",
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

    it("renders support summary and ticket rows", async () => {
        render(<SupportPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Support" })).toBeTruthy();
        });

        expect(screen.getByText("Customer billing issue")).toBeTruthy();
        expect(screen.getByText("Open Tickets")).toBeTruthy();
        expect(screen.getByText("Urgent Active")).toBeTruthy();
        expect(screen.getByRole("link", { name: "Create Ticket" })).toBeTruthy();
    });

    it("applies status and priority filters through the support service", async () => {
        render(<SupportPage />);

        await waitFor(() => {
            expect(mocks.getSupportTickets).toHaveBeenCalled();
        });

        fireEvent.change(screen.getByLabelText("Status"), {
            target: { value: "in progress" },
        });
        fireEvent.change(screen.getByLabelText("Priority"), {
            target: { value: "high" },
        });

        await waitFor(() => {
            const lastCall = mocks.getSupportTickets.mock.calls.at(-1);
            expect(lastCall?.[0]).toMatchObject({
                status: "in progress",
                priority: "high",
            });
        });
    });
});

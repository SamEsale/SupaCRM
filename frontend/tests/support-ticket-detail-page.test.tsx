import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getSupportTicketById: vi.fn(),
    updateSupportTicket: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getTenantUsers: vi.fn(),
    getDeals: vi.fn(),
    getInvoices: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("next/navigation", () => ({
    useParams: () => ({
        ticketId: "ticket-1",
    }),
}));

vi.mock("@/services/support.service", () => ({
    getSupportTicketById: mocks.getSupportTicketById,
    updateSupportTicket: mocks.updateSupportTicket,
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
}));

vi.mock("@/services/tenants.service", () => ({
    getTenantUsers: mocks.getTenantUsers,
}));

vi.mock("@/services/deals.service", () => ({
    getDeals: mocks.getDeals,
}));

vi.mock("@/services/invoices.service", () => ({
    getInvoices: mocks.getInvoices,
}));

import SupportTicketDetailPage from "@/app/(dashboard)/support/[ticketId]/page";

describe("support ticket detail page", () => {
    beforeEach(() => {
        mocks.getSupportTicketById.mockReset();
        mocks.updateSupportTicket.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getTenantUsers.mockReset();
        mocks.getDeals.mockReset();
        mocks.getInvoices.mockReset();

        mocks.getSupportTicketById.mockResolvedValue({
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
        mocks.getTenantUsers.mockResolvedValue([
            {
                user_id: "user-1",
                email: "agent@example.com",
                full_name: "Support Agent",
                user_is_active: true,
                membership_is_active: true,
                is_owner: false,
                role_names: ["support"],
                membership_created_at: "2026-04-01T10:00:00.000Z",
            },
        ]);
        mocks.getDeals.mockResolvedValue({
            items: [
                {
                    id: "deal-1",
                    tenant_id: "tenant-1",
                    name: "Renewal deal",
                    company_id: "company-1",
                    contact_id: "contact-1",
                    product_id: null,
                    amount: "1000.00",
                    currency: "USD",
                    stage: "qualified lead",
                    status: "in progress",
                    expected_close_date: null,
                    notes: null,
                    next_follow_up_at: null,
                    follow_up_note: null,
                    closed_at: null,
                    created_at: "2026-04-01T10:00:00.000Z",
                    updated_at: "2026-04-01T10:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.getInvoices.mockResolvedValue({
            items: [
                {
                    id: "invoice-1",
                    tenant_id: "tenant-1",
                    number: "INV-1001",
                    company_id: "company-1",
                    contact_id: "contact-1",
                    product_id: null,
                    source_quote_id: null,
                    issue_date: "2026-04-01",
                    due_date: "2026-04-30",
                    currency: "USD",
                    total_amount: "1000.00",
                    status: "issued",
                    notes: null,
                    created_at: "2026-04-01T10:00:00.000Z",
                    updated_at: "2026-04-01T10:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.updateSupportTicket.mockResolvedValue({
            id: "ticket-1",
            tenant_id: "tenant-1",
            title: "Customer billing issue",
            description: "Needs invoice correction",
            status: "resolved",
            priority: "high",
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
            updated_at: "2026-04-12T10:00:00.000Z",
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders CRM and commercial links and updates ticket status", async () => {
        render(<SupportTicketDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Customer billing issue" })).toBeTruthy();
        });

        expect(screen.getByRole("link", { name: "Northwind" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Alicia Andersson" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Renewal deal" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "INV-1001" })).toBeTruthy();

        fireEvent.change(screen.getByLabelText("Status"), {
            target: { value: "resolved" },
        });
        fireEvent.change(screen.getByLabelText("Priority"), {
            target: { value: "high" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

        await waitFor(() => {
            expect(mocks.updateSupportTicket).toHaveBeenCalledWith(
                "ticket-1",
                expect.objectContaining({
                    status: "resolved",
                    priority: "high",
                }),
            );
        });

        await waitFor(() => {
            expect(screen.getAllByText("Resolved").length).toBeGreaterThan(0);
        });
    });
});

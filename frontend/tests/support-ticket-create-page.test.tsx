import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    push: vi.fn(),
    refresh: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getTenantUsers: vi.fn(),
    getDeals: vi.fn(),
    getInvoices: vi.fn(),
    createSupportTicket: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: mocks.push,
        refresh: mocks.refresh,
    }),
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

vi.mock("@/services/support.service", async () => {
    const actual = await vi.importActual<typeof import("@/services/support.service")>(
        "@/services/support.service",
    );
    return {
        ...actual,
        createSupportTicket: mocks.createSupportTicket,
    };
});

import CreateSupportTicketPage from "@/app/(dashboard)/support/create/page";

describe("support create page", () => {
    beforeEach(() => {
        mocks.push.mockReset();
        mocks.refresh.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getTenantUsers.mockReset();
        mocks.getDeals.mockReset();
        mocks.getInvoices.mockReset();
        mocks.createSupportTicket.mockReset();

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
        mocks.createSupportTicket.mockResolvedValue({
            id: "ticket-1",
            tenant_id: "tenant-1",
            title: "Invoice correction needed",
            description: "Please reissue the invoice.",
            status: "open",
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
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-12T10:00:00.000Z",
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("creates a support ticket and routes to the detail page", async () => {
        render(<CreateSupportTicketPage />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: "Create ticket" })).toBeTruthy();
        });

        const titleInput = screen.getByRole("textbox", { name: "Ticket title" });
        fireEvent.input(titleInput, {
            target: { value: "Invoice correction needed" },
        });
        expect((titleInput as HTMLInputElement).value).toBe("Invoice correction needed");
        fireEvent.change(screen.getByLabelText("Description"), {
            target: { value: "Please reissue the invoice." },
        });
        fireEvent.change(screen.getByLabelText("Priority"), {
            target: { value: "high" },
        });
        fireEvent.change(screen.getByLabelText("Source"), {
            target: { value: "email" },
        });
        fireEvent.change(screen.getByLabelText("Company"), {
            target: { value: "company-1" },
        });
        fireEvent.change(screen.getByLabelText("Contact"), {
            target: { value: "contact-1" },
        });
        fireEvent.change(screen.getByLabelText("Assigned to"), {
            target: { value: "user-1" },
        });
        fireEvent.change(screen.getByLabelText("Related deal"), {
            target: { value: "deal-1" },
        });
        fireEvent.change(screen.getByLabelText("Related invoice"), {
            target: { value: "invoice-1" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Create ticket" }));

        await waitFor(() => {
            expect(mocks.createSupportTicket).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: "Invoice correction needed",
                    priority: "high",
                    source: "email",
                    company_id: "company-1",
                    contact_id: "contact-1",
                    related_invoice_id: "invoice-1",
                }),
            );
        });

        await waitFor(() => {
            expect(mocks.push).toHaveBeenCalledWith("/support/ticket-1");
            expect(mocks.refresh).toHaveBeenCalled();
        });
    });
});

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getDeals: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getProducts: vi.fn(),
    getQuotes: vi.fn(),
    getInvoices: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: mocks.push,
        refresh: mocks.refresh,
    }),
}));

vi.mock("@/services/deals.service", () => ({
    getDeals: mocks.getDeals,
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
}));

vi.mock("@/services/products.service", () => ({
    getProducts: mocks.getProducts,
}));

vi.mock("@/services/quotes.service", () => ({
    getQuotes: mocks.getQuotes,
    convertDealToQuote: vi.fn(),
}));

vi.mock("@/services/invoices.service", () => ({
    getInvoices: mocks.getInvoices,
}));

import OpportunitiesPage from "@/app/(dashboard)/sales/opportunities/page";

describe("sales opportunities page", () => {
    beforeEach(() => {
        mocks.getDeals.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getProducts.mockReset();
        mocks.getQuotes.mockReset();
        mocks.getInvoices.mockReset();
        mocks.push.mockReset();
        mocks.refresh.mockReset();

        mocks.getDeals.mockResolvedValue({
            items: [
                {
                    id: "deal-2",
                    tenant_id: "tenant-1",
                    name: "Renewal package",
                    company_id: "company-1",
                    contact_id: "contact-1",
                    product_id: null,
                    amount: "2500.00",
                    currency: "USD",
                    stage: "qualified lead",
                    status: "in progress",
                    expected_close_date: null,
                    notes: null,
                    next_follow_up_at: "2026-04-05T09:00:00.000Z",
                    follow_up_note: "Call procurement lead",
                    closed_at: null,
                    created_at: "2026-04-09T10:00:00.000Z",
                    updated_at: "2026-04-09T10:00:00.000Z",
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
        mocks.getProducts.mockResolvedValue({
            items: [],
            total: 0,
        });
        mocks.getQuotes.mockResolvedValue({
            items: [],
            total: 0,
        });
        mocks.getInvoices.mockResolvedValue({
            items: [],
            total: 0,
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("loads opportunities through the explicit opportunities deal view", async () => {
        render(<OpportunitiesPage />);

        await waitFor(() => {
        expect(mocks.getDeals).toHaveBeenCalledWith({ view: "opportunities" });
        });

        expect(screen.getByRole("heading", { name: "Opportunities" })).toBeTruthy();
        expect(screen.getByText("Renewal package")).toBeTruthy();
        expect(screen.getByText(/qualified, proposal, estimate, or negotiation stages/i)).toBeTruthy();
        expect(screen.getByText("Overdue")).toBeTruthy();
    });
});

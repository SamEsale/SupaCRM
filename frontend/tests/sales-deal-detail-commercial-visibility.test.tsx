import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getDealById: vi.fn(),
    updateDealFollowUp: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getProducts: vi.fn(),
    getQuotes: vi.fn(),
    getInvoices: vi.fn(),
    convertDealToQuote: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
    searchParams: new URLSearchParams({
        createdFrom: "lead-intake",
    }),
}));

let currentParams: Record<string, string> = {};

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "access-token",
    }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: mocks.push,
        refresh: mocks.refresh,
    }),
    useParams: () => currentParams,
    useSearchParams: () => mocks.searchParams,
}));

vi.mock("@/services/deals.service", () => ({
    getDealById: mocks.getDealById,
    deleteDeal: vi.fn(),
    updateDealFollowUp: mocks.updateDealFollowUp,
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
    convertDealToQuote: mocks.convertDealToQuote,
}));

vi.mock("@/services/invoices.service", () => ({
    getInvoices: mocks.getInvoices,
}));

import DealDetailPage from "@/app/(dashboard)/deals/[dealId]/page";

describe("sales deal detail commercial visibility", () => {
    beforeEach(() => {
        currentParams = { dealId: "deal-1" };
        mocks.getDealById.mockReset();
        mocks.getCompanies.mockReset();
        mocks.updateDealFollowUp.mockReset();
        mocks.getContacts.mockReset();
        mocks.getProducts.mockReset();
        mocks.getQuotes.mockReset();
        mocks.getInvoices.mockReset();
        mocks.convertDealToQuote.mockReset();
        mocks.push.mockReset();
        mocks.refresh.mockReset();
        mocks.searchParams = new URLSearchParams({
            createdFrom: "lead-intake",
        });

        mocks.getDealById.mockResolvedValue({
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
            notes: "Follow up with finance.",
            next_follow_up_at: "2026-04-13T09:00:00.000Z",
            follow_up_note: "Confirm finance sign-off.",
            closed_at: null,
            created_at: "2026-04-10T10:00:00.000Z",
            updated_at: "2026-04-10T10:00:00.000Z",
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
            items: [
                {
                    id: "quote-1",
                    tenant_id: "tenant-1",
                    number: "QUO-1001",
                    company_id: "company-1",
                    contact_id: "contact-1",
                    deal_id: "deal-1",
                    source_deal_id: "deal-1",
                    product_id: null,
                    issue_date: "2026-04-11",
                    expiry_date: "2026-05-11",
                    currency: "USD",
                    total_amount: "1200.00",
                    status: "accepted",
                    notes: "Created from deal Website expansion",
                    created_at: "2026-04-11T10:00:00.000Z",
                    updated_at: "2026-04-11T10:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.getInvoices.mockResolvedValue({
            items: [
                {
                    id: "invoice-1",
                    tenant_id: "tenant-1",
                    number: "INV-2001",
                    company_id: "company-1",
                    contact_id: "contact-1",
                    product_id: null,
                    source_quote_id: "quote-1",
                    issue_date: "2026-04-12",
                    due_date: "2026-05-12",
                    currency: "USD",
                    total_amount: "1200.00",
                    status: "issued",
                    notes: "Converted from quote QUO-1001",
                    created_at: "2026-04-12T10:00:00.000Z",
                    updated_at: "2026-04-12T10:00:00.000Z",
                },
            ],
            total: 1,
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("shows related quotes, derived invoices, and the lead-intake success banner", async () => {
        render(<DealDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Website expansion" })).toBeTruthy();
        });

        expect(screen.getByText(/Lead created successfully and added to the deal flow/i)).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Related quotes" })).toBeTruthy();
        expect(screen.getAllByRole("link", { name: "QUO-1001" }).length).toBeGreaterThan(0);
        expect(screen.getByRole("heading", { name: "Related invoices" })).toBeTruthy();
        expect(screen.getAllByRole("link", { name: "INV-2001" }).length).toBeGreaterThan(0);
        expect(screen.getByRole("link", { name: /View Quote \(QUO-1001\)/i })).toBeTruthy();
    });
});

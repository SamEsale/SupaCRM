import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getQuoteById: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getProducts: vi.fn(),
    getDeals: vi.fn(),
    getInvoices: vi.fn(),
    getCurrentTenant: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
    searchParams: new URLSearchParams({ createdFrom: "deal" }),
}));

let currentParams: Record<string, string> = {};

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: mocks.push, refresh: mocks.refresh }),
    useParams: () => currentParams,
    useSearchParams: () => mocks.searchParams,
}));

vi.mock("@/services/quotes.service", () => ({
    getQuoteById: mocks.getQuoteById,
    deleteQuote: vi.fn(),
    convertQuoteToInvoice: vi.fn(),
}));

vi.mock("@/services/companies.service", () => ({ getCompanies: mocks.getCompanies }));
vi.mock("@/services/contacts.service", () => ({ getContacts: mocks.getContacts }));
vi.mock("@/services/products.service", () => ({ getProducts: mocks.getProducts }));
vi.mock("@/services/deals.service", () => ({ getDeals: mocks.getDeals }));
vi.mock("@/services/invoices.service", () => ({ getInvoices: mocks.getInvoices }));
vi.mock("@/services/tenants.service", () => ({ getCurrentTenant: mocks.getCurrentTenant }));

import QuoteDetailPage from "@/app/(dashboard)/finance/quotes/[quoteId]/page";

describe("finance quote detail links", () => {
    beforeEach(() => {
        currentParams = { quoteId: "quote-1" };
        mocks.getQuoteById.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getProducts.mockReset();
        mocks.getDeals.mockReset();
        mocks.getInvoices.mockReset();
        mocks.getCurrentTenant.mockReset();
        mocks.searchParams = new URLSearchParams({ createdFrom: "deal" });

        mocks.getQuoteById.mockResolvedValue({
            id: "quote-1",
            tenant_id: "tenant-1",
            number: "QTE-000101",
            company_id: "company-1",
            contact_id: "contact-1",
            deal_id: "deal-1",
            source_deal_id: "deal-1",
            product_id: null,
            issue_date: "2026-04-12",
            expiry_date: "2026-05-12",
            currency: "USD",
            total_amount: "1200.00",
            status: "accepted",
            notes: "Prepared from deal",
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-12T10:00:00.000Z",
        });
        mocks.getCompanies.mockResolvedValue({ items: [{ id: "company-1", name: "Northwind", tenant_id: "tenant-1" }], total: 1 });
        mocks.getContacts.mockResolvedValue({ items: [{ id: "contact-1", first_name: "Alex", last_name: "Admin", company_id: "company-1", tenant_id: "tenant-1" }], total: 1 });
        mocks.getProducts.mockResolvedValue({ items: [], total: 0 });
        mocks.getDeals.mockResolvedValue({ items: [{ id: "deal-1", name: "Website expansion", company_id: "company-1", tenant_id: "tenant-1" }], total: 1 });
        mocks.getInvoices.mockResolvedValue({
            items: [{
                id: "invoice-1",
                number: "INV-000101",
                status: "issued",
                total_amount: "1200.00",
                currency: "USD",
            }],
            total: 1,
        });
        mocks.getCurrentTenant.mockResolvedValue({
            id: "tenant-1",
            name: "Northwind Workspace",
            is_active: true,
            status: "active",
            status_reason: null,
            default_currency: "SEK",
            secondary_currency: "USD",
            secondary_currency_rate: "0.100000",
            secondary_currency_rate_source: "operator_manual",
            secondary_currency_rate_as_of: "2026-04-12T09:00:00.000Z",
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-12T10:00:00.000Z",
        });
    });

    afterEach(() => cleanup());

    it("shows the created banner, related invoices, and invoice-form continuity link", async () => {
        render(<QuoteDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "QTE-000101" })).toBeTruthy();
        });

        expect(screen.getByText(/Quote created successfully from the originating deal context/i)).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Currency context" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Related invoices" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "INV-000101" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Open invoice form" }).getAttribute("href")).toBe("/finance/invoices/create?source_quote_id=quote-1");
    });

    it("hides invoice creation actions for non-accepted quotes", async () => {
        mocks.getQuoteById.mockResolvedValue({
            id: "quote-1",
            tenant_id: "tenant-1",
            number: "QTE-000101",
            company_id: "company-1",
            contact_id: "contact-1",
            deal_id: "deal-1",
            source_deal_id: "deal-1",
            product_id: null,
            issue_date: "2026-04-12",
            expiry_date: "2026-05-12",
            currency: "USD",
            total_amount: "1200.00",
            status: "draft",
            notes: "Prepared from deal",
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-12T10:00:00.000Z",
        });

        render(<QuoteDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "QTE-000101" })).toBeTruthy();
        });

        expect(screen.queryByRole("link", { name: "Open invoice form" })).toBeNull();
        expect(screen.queryByRole("button", { name: "Convert to invoice" })).toBeNull();
    });
});

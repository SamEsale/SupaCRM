import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    authState: {
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    },
    push: vi.fn(),
    refresh: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getProducts: vi.fn(),
    getDeals: vi.fn(),
    getDealById: vi.fn(),
    getCurrentTenant: vi.fn(),
    createQuote: vi.fn(),
    searchParams: new URLSearchParams({ deal_id: "deal-1" }),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => mocks.authState,
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: mocks.push,
        refresh: mocks.refresh,
    }),
    useSearchParams: () => mocks.searchParams,
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

vi.mock("@/services/deals.service", () => ({
    getDeals: mocks.getDeals,
    getDealById: mocks.getDealById,
}));

vi.mock("@/services/tenants.service", () => ({
    getCurrentTenant: mocks.getCurrentTenant,
}));

vi.mock("@/services/quotes.service", () => ({
    createQuote: mocks.createQuote,
}));

import CreateQuotePage from "@/app/(dashboard)/finance/quotes/create/page";

describe("finance quote create flow", () => {
    beforeEach(() => {
        mocks.push.mockReset();
        mocks.refresh.mockReset();
        mocks.authState.isReady = true;
        mocks.authState.isAuthenticated = true;
        mocks.authState.accessToken = "token";
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getProducts.mockReset();
        mocks.getDeals.mockReset();
        mocks.getDealById.mockReset();
        mocks.getCurrentTenant.mockReset();
        mocks.createQuote.mockReset();
        mocks.searchParams = new URLSearchParams({ deal_id: "deal-1" });

        mocks.getCompanies.mockResolvedValue({
            items: [{ id: "company-1", name: "Northwind", tenant_id: "tenant-1" }],
            total: 1,
        });
        mocks.getContacts.mockResolvedValue({
            items: [{ id: "contact-1", first_name: "Alex", last_name: "Admin", company_id: "company-1", tenant_id: "tenant-1" }],
            total: 1,
        });
        mocks.getProducts.mockResolvedValue({ items: [], total: 0 });
        mocks.getCurrentTenant.mockResolvedValue({
            id: "tenant-1",
            name: "Northwind Workspace",
            is_active: true,
            status: "active",
            status_reason: null,
            default_currency: "EUR",
            secondary_currency: "USD",
            created_at: "2026-04-01T10:00:00.000Z",
            updated_at: "2026-04-01T10:00:00.000Z",
        });
        mocks.getDeals.mockResolvedValue({
            items: [{
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
                expected_close_date: "2026-05-01",
                notes: "Carry the commercial context forward.",
                next_follow_up_at: null,
                follow_up_note: null,
                closed_at: null,
                created_at: "2026-04-01T10:00:00.000Z",
                updated_at: "2026-04-01T10:00:00.000Z",
            }],
            total: 1,
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
            expected_close_date: "2026-05-01",
            notes: "Carry the commercial context forward.",
            next_follow_up_at: null,
            follow_up_note: null,
            closed_at: null,
            created_at: "2026-04-01T10:00:00.000Z",
            updated_at: "2026-04-01T10:00:00.000Z",
        });
        mocks.createQuote.mockResolvedValue({
            id: "quote-1",
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("prefills from the deal context and routes to the created quote detail page", async () => {
        render(<CreateQuotePage />);

        await waitFor(() => {
            expect(screen.getByText(/Creating this quote from deal/i)).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: "Create Quote" }));

        await waitFor(() => {
            expect(mocks.createQuote).toHaveBeenCalledWith(
                expect.objectContaining({
                    company_id: "company-1",
                    contact_id: "contact-1",
                    deal_id: "deal-1",
                    source_deal_id: "deal-1",
                    currency: "USD",
                    total_amount: 1200,
                }),
            );
        });

        expect(mocks.push).toHaveBeenCalledWith("/finance/quotes/quote-1?createdFrom=deal");
        expect(mocks.refresh).toHaveBeenCalled();
    });

    it("does not call protected quote create loaders before auth readiness", async () => {
        mocks.authState.isReady = false;

        const view = render(<CreateQuotePage />);

        await waitFor(() => {
            expect(mocks.getCompanies).not.toHaveBeenCalled();
            expect(mocks.getContacts).not.toHaveBeenCalled();
            expect(mocks.getProducts).not.toHaveBeenCalled();
            expect(mocks.getCurrentTenant).not.toHaveBeenCalled();
            expect(mocks.getDeals).not.toHaveBeenCalled();
            expect(mocks.getDealById).not.toHaveBeenCalled();
        });

        mocks.authState.isReady = true;
        view.rerender(<CreateQuotePage />);

        await waitFor(() => {
            expect(mocks.getCompanies).toHaveBeenCalledTimes(1);
            expect(mocks.getContacts).toHaveBeenCalledTimes(1);
            expect(mocks.getProducts).toHaveBeenCalledTimes(1);
            expect(mocks.getCurrentTenant).toHaveBeenCalledTimes(1);
            expect(mocks.getDeals).toHaveBeenCalledTimes(1);
        });
    });

    it("uses the tenant default currency when no deal prefill is present", async () => {
        mocks.searchParams = new URLSearchParams();

        render(<CreateQuotePage />);

        await waitFor(() => {
            expect(mocks.getCurrentTenant).toHaveBeenCalledTimes(1);
        });

        await waitFor(() => {
            expect(screen.getByDisplayValue("EUR")).toBeTruthy();
        });
    });
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getDealById: vi.fn(),
    deleteDeal: vi.fn(),
    updateDealFollowUp: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getProducts: vi.fn(),
    getQuotes: vi.fn(),
    getInvoices: vi.fn(),
    convertDealToQuote: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
    searchParams: new URLSearchParams(),
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
    deleteDeal: mocks.deleteDeal,
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

vi.mock("@/services/invoices.service", () => ({
    getInvoices: mocks.getInvoices,
}));

vi.mock("@/services/quotes.service", () => ({
    getQuotes: mocks.getQuotes,
    convertDealToQuote: mocks.convertDealToQuote,
}));

import DealDetailPage from "@/app/(dashboard)/deals/[dealId]/page";

describe("sales deal detail delete action", () => {
    beforeEach(() => {
        currentParams = { dealId: "deal-1" };
        mocks.getDealById.mockReset();
        mocks.deleteDeal.mockReset();
        mocks.updateDealFollowUp.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getProducts.mockReset();
        mocks.getQuotes.mockReset();
        mocks.getInvoices.mockReset();
        mocks.convertDealToQuote.mockReset();
        mocks.push.mockReset();
        mocks.refresh.mockReset();
        mocks.searchParams = new URLSearchParams();

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
            next_follow_up_at: null,
            follow_up_note: null,
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
            items: [],
            total: 0,
        });
        mocks.getInvoices.mockResolvedValue({
            items: [],
            total: 0,
        });

        vi.spyOn(window, "confirm").mockReturnValue(true);
    });

    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
    });

    it("deletes the deal from the real detail page and navigates back to the deals list", async () => {
        mocks.deleteDeal.mockResolvedValue({
            success: true,
            message: "Deal deleted successfully",
        });

        render(<DealDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Website expansion" })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: "Delete Deal" }));

        await waitFor(() => {
            expect(window.confirm).toHaveBeenCalled();
            expect(mocks.deleteDeal).toHaveBeenCalledWith("deal-1");
            expect(mocks.push).toHaveBeenCalledWith("/deals");
            expect(mocks.refresh).toHaveBeenCalled();
        });
    });

    it("renders a clear API error when deleting fails", async () => {
        mocks.deleteDeal.mockRejectedValueOnce({
            response: {
                data: {
                    detail: "Deal cannot be deleted while conversion is in progress.",
                },
            },
        });

        render(<DealDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Website expansion" })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: "Delete Deal" }));

        await waitFor(() => {
            expect(
                screen.getByText("Deal cannot be deleted while conversion is in progress."),
            ).toBeTruthy();
        });
    });
});

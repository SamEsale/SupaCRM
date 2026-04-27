import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getProducts: vi.fn(),
    getDeals: vi.fn(),
    getQuoteById: vi.fn(),
    createInvoice: vi.fn(),
    createQuote: vi.fn(),
    updateQuote: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
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
    useRouter: () => ({
        push: mocks.push,
        refresh: mocks.refresh,
    }),
    useParams: () => currentParams,
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
}));

vi.mock("@/services/invoices.service", () => ({
    createInvoice: mocks.createInvoice,
}));

vi.mock("@/services/quotes.service", () => ({
    createQuote: mocks.createQuote,
    getQuoteById: mocks.getQuoteById,
    updateQuote: mocks.updateQuote,
}));

import CreateInvoicePage from "@/app/(dashboard)/finance/invoices/create/page";
import EditQuotePage from "@/app/(dashboard)/finance/quotes/[quoteId]/edit/page";
import CreateQuotePage from "@/app/(dashboard)/finance/quotes/create/page";
import {
    sanitizeStrictDecimalInput,
    shouldBlockStrictDecimalKey,
} from "@/components/finance/amount-utils";
import DealCreateForm from "@/components/deals/DealCreateForm";
import type { Company } from "@/types/crm";

function setupReferenceData(): void {
    mocks.getCompanies.mockResolvedValue({
        items: [{ id: "company-1", name: "Acme Inc" }],
        total: 1,
    });
    mocks.getContacts.mockResolvedValue({
        items: [],
        total: 0,
    });
    mocks.getProducts.mockResolvedValue({
        items: [],
        total: 0,
    });
    mocks.getDeals.mockResolvedValue({
        items: [],
        total: 0,
    });
    mocks.getQuoteById.mockResolvedValue({
        id: "quote-1",
        tenant_id: "tenant-1",
        number: "Q-0001",
        company_id: "company-1",
        contact_id: null,
        deal_id: null,
        source_deal_id: null,
        product_id: null,
        issue_date: "2026-01-10",
        expiry_date: "2026-01-20",
        currency: "USD",
        total_amount: "1000",
        status: "draft",
        notes: null,
        created_at: "2026-01-01T00:00:00.000Z",
        updated_at: "2026-01-01T00:00:00.000Z",
    });
    mocks.createInvoice.mockResolvedValue({ id: "invoice-1" });
    mocks.createQuote.mockResolvedValue({ id: "quote-1" });
    mocks.updateQuote.mockResolvedValue({ id: "quote-1" });
}

function fillInvoiceForm(amount: string): void {
    fireEvent.change(screen.getAllByRole("combobox")[0], {
        target: { value: "company-1" },
    });
    const dateInputs = document.querySelectorAll('input[type="date"]');
    fireEvent.change(dateInputs[0], { target: { value: "2026-01-10" } });
    fireEvent.change(dateInputs[1], { target: { value: "2026-01-20" } });
    fireEvent.change(screen.getByPlaceholderText(/e\.g\. usd/i), {
        target: { value: "USD" },
    });
    fireEvent.change(screen.getByPlaceholderText(/e\.g\. 1000\.00/i), {
        target: { value: amount },
    });
}

function fillQuoteForm(amount: string): void {
    fireEvent.change(screen.getAllByRole("combobox")[0], {
        target: { value: "company-1" },
    });
    const dateInputs = document.querySelectorAll('input[type="date"]');
    fireEvent.change(dateInputs[0], { target: { value: "2026-01-10" } });
    fireEvent.change(dateInputs[1], { target: { value: "2026-01-20" } });
    fireEvent.change(screen.getByPlaceholderText(/e\.g\. usd/i), {
        target: { value: "USD" },
    });
    fireEvent.change(screen.getByPlaceholderText(/e\.g\. 1000\.00/i), {
        target: { value: amount },
    });
}

beforeEach(() => {
    mocks.push.mockReset();
    mocks.refresh.mockReset();
    mocks.getQuoteById.mockReset();
    mocks.createInvoice.mockReset();
    mocks.createQuote.mockReset();
    mocks.updateQuote.mockReset();
    currentParams = {};
    setupReferenceData();
});

afterEach(() => {
    cleanup();
});

describe("finance amount validation", () => {
    it("keeps strict decimal money inputs free of exponent and sign characters", () => {
        expect(sanitizeStrictDecimalInput("12e3")).toBe("123");
        expect(sanitizeStrictDecimalInput("10E3")).toBe("103");
        expect(sanitizeStrictDecimalInput("99+-")).toBe("99");
        expect(shouldBlockStrictDecimalKey("e")).toBe(true);
        expect(shouldBlockStrictDecimalKey("E")).toBe(true);
        expect(shouldBlockStrictDecimalKey("+")).toBe(true);
        expect(shouldBlockStrictDecimalKey("-")).toBe(true);
        expect(shouldBlockStrictDecimalKey("1")).toBe(false);
    });

    it("invoice create sanitizes pasted letters and accepts strict decimal input", async () => {
        render(<CreateInvoicePage />);

        await waitFor(() => {
            expect(mocks.getCompanies).toHaveBeenCalled();
        });

        fillInvoiceForm("12e3");
        expect((screen.getByPlaceholderText(/e\.g\. 1000\.00/i) as HTMLInputElement).value).toBe(
            "123",
        );
        fireEvent.click(screen.getByRole("button", { name: /create invoice/i }));

        await waitFor(() => {
            expect(mocks.createInvoice).toHaveBeenCalledTimes(1);
        });

        expect(mocks.createInvoice).toHaveBeenCalledWith(
            expect.objectContaining({
                company_id: "company-1",
                currency: "USD",
                total_amount: 123,
            }),
        );
    });

    it("quote create sanitizes pasted letters and rejects invalid numeric input precisely", async () => {
        render(<CreateQuotePage />);

        await waitFor(() => {
            expect(mocks.getCompanies).toHaveBeenCalled();
        });

        fillQuoteForm("12e3");
        expect((screen.getByPlaceholderText(/e\.g\. 1000\.00/i) as HTMLInputElement).value).toBe(
            "123",
        );
        fireEvent.click(screen.getByRole("button", { name: /create quote/i }));

        await waitFor(() => {
            expect(mocks.createQuote).toHaveBeenCalledTimes(1);
        });

        expect(mocks.createQuote).toHaveBeenCalledWith(
            expect.objectContaining({
                company_id: "company-1",
                currency: "USD",
                total_amount: 123,
            }),
        );
    });

    it("quote edit sanitizes pasted letters and accepts strict decimal input", async () => {
        currentParams = { quoteId: "quote-1" };

        render(<EditQuotePage />);

        await waitFor(() => {
            expect(mocks.getQuoteById).toHaveBeenCalledWith("quote-1");
        });

        fireEvent.change(screen.getByPlaceholderText(/e\.g\. 1000\.00/i), {
            target: { value: "12e3" },
        });
        expect((screen.getByPlaceholderText(/e\.g\. 1000\.00/i) as HTMLInputElement).value).toBe(
            "123",
        );
        fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

        await waitFor(() => {
            expect(mocks.updateQuote).toHaveBeenCalledTimes(1);
        });

        expect(mocks.updateQuote).toHaveBeenCalledWith(
            "quote-1",
            expect.objectContaining({
                company_id: "company-1",
                currency: "USD",
                total_amount: 123,
            }),
        );
    });

    it("deal create sanitizes pasted letters and accepts strict decimal input", async () => {
        const companies: Company[] = [
            {
                id: "company-1",
                tenant_id: "tenant-1",
                name: "Acme Inc",
                website: null,
                email: null,
                phone: null,
                industry: null,
                address: null,
                vat_number: null,
                registration_number: null,
                notes: null,
                created_at: "2026-01-01T00:00:00.000Z",
                updated_at: "2026-01-01T00:00:00.000Z",
            },
        ];

        const onSubmit = vi.fn();

        render(
            <DealCreateForm
                companies={companies}
                contacts={[]}
                products={[]}
                onSubmit={onSubmit}
            />,
        );

        fireEvent.change(screen.getByLabelText(/^Deal name$/i), {
            target: { value: "New opportunity" },
        });
        fireEvent.change(screen.getByLabelText(/^Company$/i), {
            target: { value: "company-1" },
        });
        fireEvent.change(screen.getByLabelText(/^Amount$/i), {
            target: { value: "12e3" },
        });
        expect((screen.getByLabelText(/^Amount$/i) as HTMLInputElement).value).toBe("123");
        fireEvent.change(screen.getByLabelText(/^Currency$/i), {
            target: { value: "USD" },
        });

        fireEvent.click(screen.getByRole("button", { name: /create deal/i }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledTimes(1);
        });

        expect(onSubmit).toHaveBeenCalledWith(
            expect.objectContaining({
                company_id: "company-1",
                currency: "USD",
                amount: "123",
            }),
        );
    });
});

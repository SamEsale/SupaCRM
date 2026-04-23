import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    push: vi.fn(),
    refresh: vi.fn(),
    getJournalEntries: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getProducts: vi.fn(),
    getCurrentTenant: vi.fn(),
    getQuoteById: vi.fn(),
    getDealById: vi.fn(),
    getInvoiceById: vi.fn(),
    createInvoice: vi.fn(),
    deleteInvoice: vi.fn(),
    getPayments: vi.fn(),
    getInvoicePaymentSummary: vi.fn(),
    createPayment: vi.fn(),
    searchParams: new URLSearchParams({ source_quote_id: "quote-1", createdFrom: "quote" }),
}));

let currentParams: Record<string, string> = {};

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("@/services/accounting.service", () => ({
    getJournalEntries: mocks.getJournalEntries,
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: mocks.push, refresh: mocks.refresh }),
    useParams: () => currentParams,
    useSearchParams: () => mocks.searchParams,
}));

vi.mock("@/services/companies.service", () => ({ getCompanies: mocks.getCompanies }));
vi.mock("@/services/contacts.service", () => ({ getContacts: mocks.getContacts }));
vi.mock("@/services/products.service", () => ({ getProducts: mocks.getProducts }));
vi.mock("@/services/tenants.service", () => ({ getCurrentTenant: mocks.getCurrentTenant }));
vi.mock("@/services/quotes.service", () => ({ getQuoteById: mocks.getQuoteById }));
vi.mock("@/services/deals.service", () => ({ getDealById: mocks.getDealById }));
vi.mock("@/services/invoices.service", () => ({
    createInvoice: mocks.createInvoice,
    getInvoiceById: mocks.getInvoiceById,
    deleteInvoice: mocks.deleteInvoice,
}));

vi.mock("@/services/payments.service", () => ({
    getPayments: mocks.getPayments,
    getInvoicePaymentSummary: mocks.getInvoicePaymentSummary,
    createPayment: mocks.createPayment,
}));

import CreateInvoicePage from "@/app/(dashboard)/finance/invoices/create/page";
import InvoiceDetailPage from "@/app/(dashboard)/finance/invoices/[invoiceId]/page";

describe("finance invoice flow", () => {
    beforeEach(() => {
        currentParams = { invoiceId: "invoice-1" };
        mocks.push.mockReset();
        mocks.refresh.mockReset();
        mocks.getJournalEntries.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getProducts.mockReset();
        mocks.getCurrentTenant.mockReset();
        mocks.getQuoteById.mockReset();
        mocks.getDealById.mockReset();
        mocks.getInvoiceById.mockReset();
        mocks.createInvoice.mockReset();
        mocks.deleteInvoice.mockReset();
        mocks.getPayments.mockReset();
        mocks.getInvoicePaymentSummary.mockReset();
        mocks.createPayment.mockReset();
        mocks.searchParams = new URLSearchParams({ source_quote_id: "quote-1", createdFrom: "quote" });

        mocks.getCompanies.mockResolvedValue({ items: [{ id: "company-1", name: "Northwind", tenant_id: "tenant-1" }], total: 1 });
        mocks.getContacts.mockResolvedValue({ items: [{ id: "contact-1", first_name: "Alex", last_name: "Admin", company_id: "company-1", tenant_id: "tenant-1" }], total: 1 });
        mocks.getProducts.mockResolvedValue({ items: [], total: 0 });
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
            status: "won",
            expected_close_date: null,
            notes: null,
            next_follow_up_at: null,
            follow_up_note: null,
            closed_at: null,
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-12T10:00:00.000Z",
        });
        mocks.createInvoice.mockResolvedValue({ id: "invoice-1" });
        mocks.getJournalEntries.mockResolvedValue({
            items: [
                {
                    id: "journal-1",
                    tenant_id: "tenant-1",
                    entry_date: "2026-04-12",
                    memo: "Invoice INV-000101 issued",
                    source_type: "invoice",
                    source_id: "invoice-1",
                    source_event: "invoice_issued",
                    currency: "USD",
                    total_debit: "1200.00",
                    total_credit: "1200.00",
                    created_at: "2026-04-12T10:00:00.000Z",
                    lines: [],
                },
            ],
            total: 1,
        });
        mocks.getInvoiceById.mockResolvedValue({
            id: "invoice-1",
            tenant_id: "tenant-1",
            number: "INV-000101",
            company_id: "company-1",
            contact_id: "contact-1",
            product_id: null,
            source_quote_id: "quote-1",
            issue_date: "2026-04-12",
            due_date: "2026-05-12",
            currency: "USD",
            total_amount: "1200.00",
            status: "issued",
            notes: "Converted from quote",
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-12T10:00:00.000Z",
        });
        mocks.getPayments.mockResolvedValue({
            items: [
                {
                    id: "payment-1",
                    tenant_id: "tenant-1",
                    invoice_id: "invoice-1",
                    amount: "300.00",
                    currency: "USD",
                    method: "bank_transfer",
                    status: "completed",
                    payment_date: "2026-04-12T14:00:00.000Z",
                    external_reference: "BT-100",
                    notes: "Deposit received",
                    created_at: "2026-04-12T14:00:00.000Z",
                    updated_at: "2026-04-12T14:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.getInvoicePaymentSummary.mockResolvedValue({
            invoice_id: "invoice-1",
            currency: "USD",
            invoice_total_amount: "1200.00",
            completed_amount: "300.00",
            pending_amount: "0.00",
            outstanding_amount: "900.00",
            payment_count: 1,
            completed_payment_count: 1,
            pending_payment_count: 0,
            payment_state: "partially paid",
        });
        mocks.createPayment.mockResolvedValue({
            id: "payment-2",
            tenant_id: "tenant-1",
            invoice_id: "invoice-1",
            amount: "900.00",
            currency: "USD",
            method: "cash",
            status: "completed",
            payment_date: "2026-04-13T09:30:00.000Z",
            external_reference: null,
            notes: "Final settlement",
            created_at: "2026-04-13T09:30:00.000Z",
            updated_at: "2026-04-13T09:30:00.000Z",
        });
    });

    afterEach(() => cleanup());

    it("prefills from the quote context and routes to the created invoice detail page", async () => {
        render(<CreateInvoicePage />);

        await waitFor(() => {
            expect(screen.getByText(/Creating this invoice from quote/i)).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: "Create Invoice" }));

        await waitFor(() => {
            expect(mocks.createInvoice).toHaveBeenCalledWith(
                expect.objectContaining({
                    company_id: "company-1",
                    contact_id: "contact-1",
                    source_quote_id: "quote-1",
                    currency: "USD",
                    total_amount: 1200,
                }),
            );
        });

        expect(mocks.push).toHaveBeenCalledWith("/finance/invoices/invoice-1?createdFrom=quote");
    });

    it("uses the tenant default currency when no quote prefill is present", async () => {
        mocks.searchParams = new URLSearchParams();

        render(<CreateInvoicePage />);

        await waitFor(() => {
            expect(mocks.getCurrentTenant).toHaveBeenCalledTimes(1);
        });

        await waitFor(() => {
            expect(screen.getByDisplayValue("SEK")).toBeTruthy();
        });
    });

    it("shows source quote, source deal, and honest payment visibility on invoice detail", async () => {
        render(<InvoiceDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "INV-000101" })).toBeTruthy();
        });

        await waitFor(() => {
            expect(screen.getByText(/Payment state/i)).toBeTruthy();
        });

        expect(screen.getByText(/Invoice created successfully from the quote context/i)).toBeTruthy();
        expect(screen.getByRole("link", { name: "QTE-000101" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Website expansion" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Payments" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Currency context" })).toBeTruthy();
        expect(screen.getByText(/Secondary currency view/i)).toBeTruthy();
        expect(screen.getByText(/^partially paid$/i)).toBeTruthy();
        expect(screen.getByText(/Deposit received/i)).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Accounting visibility" })).toBeTruthy();
        expect(screen.getByText(/Invoice INV-000101 issued/i)).toBeTruthy();
        expect(screen.getByRole("link", { name: "View accounting entries" }).getAttribute("href")).toBe(
            "/finance/accounting?source_type=invoice&source_id=invoice-1",
        );
    });

    it("records a payment from invoice detail and reloads the payment snapshot", async () => {
        render(<InvoiceDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: "Record payment" })).toBeTruthy();
        });

        fireEvent.change(screen.getByLabelText(/Amount/i), {
            target: { value: "900.00" },
        });
        fireEvent.change(screen.getByLabelText(/Method/i), {
            target: { value: "cash" },
        });
        fireEvent.change(screen.getByLabelText(/Notes/i), {
            target: { value: "Final settlement" },
        });

        fireEvent.click(screen.getByRole("button", { name: "Record payment" }));

        await waitFor(() => {
            expect(mocks.createPayment).toHaveBeenCalledWith(
                expect.objectContaining({
                    invoice_id: "invoice-1",
                    amount: 900,
                    currency: "USD",
                    method: "cash",
                    status: "completed",
                    notes: "Final settlement",
                }),
            );
        });

        expect(mocks.getPayments.mock.calls.length).toBeGreaterThanOrEqual(2);
        expect(mocks.getInvoicePaymentSummary.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
});

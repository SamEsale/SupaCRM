import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    authState: {
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    },
    getCurrentTenant: vi.fn(),
    getExpenses: vi.fn(),
    createExpense: vi.fn(),
    updateExpense: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => mocks.authState,
}));

vi.mock("@/services/tenants.service", () => ({
    getCurrentTenant: mocks.getCurrentTenant,
}));

vi.mock("@/services/expenses.service", () => ({
    getExpenses: mocks.getExpenses,
    createExpense: mocks.createExpense,
    updateExpense: mocks.updateExpense,
}));

import ExpensesPage from "@/app/(dashboard)/finance/expenses/page";

describe("finance expenses page", () => {
    beforeEach(() => {
        mocks.authState.isReady = true;
        mocks.authState.isAuthenticated = true;
        mocks.authState.accessToken = "token";
        mocks.getCurrentTenant.mockReset();
        mocks.getExpenses.mockReset();
        mocks.createExpense.mockReset();
        mocks.updateExpense.mockReset();

        mocks.getCurrentTenant.mockResolvedValue({
            id: "tenant-1",
            name: "Northwind Workspace",
            is_active: true,
            status: "active",
            status_reason: null,
            default_currency: "SEK",
            secondary_currency: "EUR",
            secondary_currency_rate: "0.091500",
            secondary_currency_rate_source: "operator_manual",
            secondary_currency_rate_as_of: "2026-04-12T09:00:00.000Z",
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-12T10:00:00.000Z",
        });
        mocks.getExpenses.mockResolvedValue({
            items: [
                {
                    id: "expense-1",
                    tenant_id: "tenant-1",
                    title: "Meta ads",
                    description: "Launch spend",
                    amount: "120.00",
                    currency: "SEK",
                    expense_date: "2026-04-11",
                    category: "marketing",
                    status: "approved",
                    vendor_name: "Meta",
                    created_at: "2026-04-12T10:00:00.000Z",
                    updated_at: "2026-04-12T10:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.createExpense.mockResolvedValue({
            id: "expense-2",
            tenant_id: "tenant-1",
            title: "Cloud hosting",
            description: "Infra bill",
            amount: "199.00",
            currency: "SEK",
            expense_date: "2026-04-14",
            category: "operations",
            status: "submitted",
            vendor_name: "OpenCloud",
            created_at: "2026-04-14T10:00:00.000Z",
            updated_at: "2026-04-14T10:00:00.000Z",
        });
        mocks.updateExpense.mockResolvedValue({
            id: "expense-1",
            tenant_id: "tenant-1",
            title: "Meta ads",
            description: "Launch spend",
            amount: "120.00",
            currency: "SEK",
            expense_date: "2026-04-11",
            category: "marketing",
            status: "paid",
            vendor_name: "Meta",
            created_at: "2026-04-12T10:00:00.000Z",
            updated_at: "2026-04-14T10:00:00.000Z",
        });
    });

    afterEach(() => cleanup());

    it("does not call protected expense loaders before auth readiness", async () => {
        mocks.authState.isReady = false;

        const view = render(<ExpensesPage />);

        await waitFor(() => {
            expect(mocks.getCurrentTenant).not.toHaveBeenCalled();
            expect(mocks.getExpenses).not.toHaveBeenCalled();
        });

        mocks.authState.isReady = true;
        view.rerender(<ExpensesPage />);

        await waitFor(() => {
            expect(mocks.getCurrentTenant).toHaveBeenCalledTimes(1);
            expect(mocks.getExpenses).toHaveBeenCalledTimes(1);
        });
    });

    it("renders expenses and records a new expense", async () => {
        render(<ExpensesPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Expenses" })).toBeTruthy();
        });

        expect(screen.getByText(/Meta ads/i)).toBeTruthy();
        expect(screen.getByText(/Manual FX is active/i)).toBeTruthy();

        fireEvent.change(screen.getByLabelText(/Title/i), {
            target: { value: "Cloud hosting" },
        });
        fireEvent.change(screen.getByLabelText(/Vendor \/ company/i), {
            target: { value: "OpenCloud" },
        });
        fireEvent.change(screen.getByLabelText(/Amount/i), {
            target: { value: "199.00" },
        });
        fireEvent.change(screen.getByLabelText(/^Currency$/i), {
            target: { value: "SEK" },
        });
        fireEvent.change(screen.getByLabelText(/Expense date/i), {
            target: { value: "2026-04-14" },
        });
        fireEvent.change(screen.getByLabelText(/Category/i), {
            target: { value: "operations" },
        });
        fireEvent.change(screen.getByLabelText(/Status/i), {
            target: { value: "submitted" },
        });
        fireEvent.change(screen.getByLabelText(/Notes/i), {
            target: { value: "Infra bill" },
        });
        fireEvent.click(screen.getByRole("button", { name: /Record expense/i }));

        await waitFor(() => {
            expect(mocks.createExpense).toHaveBeenCalledWith({
                title: "Cloud hosting",
                description: "Infra bill",
                amount: 199,
                currency: "SEK",
                expense_date: "2026-04-14",
                category: "operations",
                status: "submitted",
                vendor_name: "OpenCloud",
            });
        });
    });

    it("allows editing an unpaid expense", async () => {
        render(<ExpensesPage />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: "Edit" })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: "Edit" }));
        fireEvent.change(screen.getByLabelText(/Status/i), {
            target: { value: "paid" },
        });
        fireEvent.click(screen.getByRole("button", { name: /Save expense changes/i }));

        await waitFor(() => {
            expect(mocks.updateExpense).toHaveBeenCalledWith(
                "expense-1",
                expect.objectContaining({
                    status: "paid",
                    title: "Meta ads",
                }),
            );
        });
    });
});

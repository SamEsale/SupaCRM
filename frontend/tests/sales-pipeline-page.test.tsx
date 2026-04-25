import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getDeals: vi.fn(),
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getPipelineReport: vi.fn(),
    updateDeal: vi.fn(),
}));

vi.mock("@/services/deals.service", () => ({
    getDeals: mocks.getDeals,
    getPipelineReport: mocks.getPipelineReport,
    updateDeal: mocks.updateDeal,
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
}));

import SalesPipelinePage from "@/app/(dashboard)/sales/pipeline/page";

const companiesResponse = {
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
};

const contactsResponse = {
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
};

describe("sales pipeline page", () => {
    beforeEach(() => {
        mocks.getDeals.mockReset();
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.getPipelineReport.mockReset();
        mocks.updateDeal.mockReset();

        mocks.getDeals.mockResolvedValue({
            items: [
                {
                    id: "deal-1",
                    tenant_id: "tenant-1",
                    name: "Website expansion",
                    company_id: "company-1",
                    contact_id: "contact-1",
                    product_id: null,
                    amount: "1200.00",
                    currency: "USD",
                    stage: "new lead",
                    status: "open",
                    expected_close_date: null,
                    notes: null,
                    created_at: "2026-04-10T10:00:00.000Z",
                    updated_at: "2026-04-10T10:00:00.000Z",
                },
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
                    created_at: "2026-04-09T10:00:00.000Z",
                    updated_at: "2026-04-09T10:00:00.000Z",
                },
            ],
            total: 2,
        });
        mocks.getCompanies.mockResolvedValue(companiesResponse);
        mocks.getContacts.mockResolvedValue(contactsResponse);
        mocks.getPipelineReport.mockResolvedValue({
            items: [
                { stage: "new lead", count: 1 },
                { stage: "qualified lead", count: 1 },
                { stage: "proposal sent", count: 0 },
                { stage: "estimate sent", count: 0 },
                { stage: "negotiating contract terms", count: 0 },
                { stage: "contract signed", count: 0 },
                { stage: "deal not secured", count: 0 },
            ],
            total: 2,
        });
        mocks.updateDeal.mockResolvedValue({
            id: "deal-1",
            tenant_id: "tenant-1",
            name: "Website expansion",
            company_id: "company-1",
            contact_id: "contact-1",
            product_id: null,
            amount: "1200.00",
            currency: "USD",
            stage: "qualified lead",
            status: "open",
            expected_close_date: null,
            notes: null,
            created_at: "2026-04-10T10:00:00.000Z",
            updated_at: "2026-04-10T10:05:00.000Z",
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders the real pipeline grouped by stage with live counts", async () => {
        render(<SalesPipelinePage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Sales Pipeline" })).toBeTruthy();
            expect(screen.getByRole("heading", { name: "New Lead" })).toBeTruthy();
            expect(screen.getByRole("heading", { name: "Qualified Lead" })).toBeTruthy();
        });

        expect(screen.getByText("Website expansion")).toBeTruthy();
        expect(screen.getByText("Renewal package")).toBeTruthy();
        expect(screen.getAllByText("1 deal").length).toBeGreaterThan(0);
    });

    it("moves a deal to the next stage using the existing deal update flow", async () => {
        render(<SalesPipelinePage />);

        await waitFor(() => {
            expect(screen.getByText("Website expansion")).toBeTruthy();
        });

        const card = screen.getByText("Website expansion").closest("article");
        expect(card).toBeTruthy();
        const scoped = within(card as HTMLElement);

        fireEvent.change(scoped.getByLabelText(/Move stage/i), {
            target: { value: "qualified lead" },
        });
        fireEvent.click(scoped.getByRole("button", { name: "Move" }));

        await waitFor(() => {
            expect(mocks.updateDeal).toHaveBeenCalledWith("deal-1", {
                stage: "qualified lead",
                status: "open",
            });
        });
        await waitFor(() => {
            expect(
                screen.getByText("Website expansion moved to Qualified Lead."),
            ).toBeTruthy();
        });
    });

    it("renders a useful error state when the pipeline request fails", async () => {
        mocks.getDeals.mockRejectedValueOnce({
            response: {
                status: 403,
                data: {
                    error: {
                        code: "forbidden",
                        message: "You do not have permission to perform this action.",
                    },
                },
            },
            message: "Request failed with status code 403",
        });

        render(<SalesPipelinePage />);

        await waitFor(() => {
            expect(
                screen.getByRole("heading", { name: "Failed to load pipeline" }),
            ).toBeTruthy();
        });
        expect(screen.getByText("You do not have permission to perform this action.")).toBeTruthy();
        expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
    });
});

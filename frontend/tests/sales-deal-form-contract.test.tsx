import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/services/deals.service", () => ({
    createDeal: vi.fn(),
}));

import DealCreateForm from "@/components/deals/DealCreateForm";

describe("sales deal form contract", () => {
    afterEach(() => {
        cleanup();
    });

    it("only exposes the supported deal status options after contract cleanup", () => {
        render(
            <DealCreateForm
                companies={[
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
                ]}
                contacts={[]}
                products={[]}
            />,
        );

        const statusSelect = screen.getByLabelText(/^Status$/i);
        const statusOptions = within(statusSelect).getAllByRole("option");
        const optionLabels = statusOptions.map((option) => option.textContent?.trim());

        expect(optionLabels).toEqual(["Open", "In Progress", "Won", "Lost"]);
        expect(screen.queryByRole("option", { name: /archived/i })).toBeNull();
    });
});

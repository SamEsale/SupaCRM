import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    pathname: "/settings/company",
    getCurrentTenant: vi.fn(),
    updateCurrentTenant: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    usePathname: () => mocks.pathname,
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("@/services/tenants.service", () => ({
    getCurrentTenant: mocks.getCurrentTenant,
    updateCurrentTenant: mocks.updateCurrentTenant,
}));

import CompanySettingsPage from "@/app/(dashboard)/settings/company/page";

describe("settings company page", () => {
    beforeEach(() => {
        mocks.getCurrentTenant.mockReset();
        mocks.updateCurrentTenant.mockReset();
        mocks.getCurrentTenant.mockResolvedValue({
            id: "tenant-1",
            name: "Northwind Workspace",
            is_active: true,
            status: "active",
            status_reason: null,
            legal_name: "Northwind Labs AB",
            address_line_1: "Sveavagen 1",
            address_line_2: null,
            city: "Stockholm",
            state_region: "Stockholm County",
            postal_code: "111 57",
            country: "Sweden",
            vat_number: "SE123456789001",
            default_currency: "SEK",
            secondary_currency: "EUR",
            secondary_currency_rate: "0.091500",
            secondary_currency_rate_source: "operator_manual",
            secondary_currency_rate_as_of: "2026-04-13T10:30:00.000Z",
            logo_file_key: null,
            brand_primary_color: "#2563EB",
            brand_secondary_color: "#1D4ED8",
            sidebar_background_color: "#111827",
            sidebar_text_color: "#FFFFFF",
            created_at: "2026-04-13T10:00:00.000Z",
            updated_at: "2026-04-13T10:00:00.000Z",
        });
        mocks.updateCurrentTenant.mockResolvedValue({
            id: "tenant-1",
            name: "Northwind CRM",
            is_active: true,
            status: "active",
            status_reason: null,
            legal_name: "Northwind Labs AB",
            address_line_1: "Sveavagen 2",
            address_line_2: "Floor 4",
            city: "Stockholm",
            state_region: "Stockholm County",
            postal_code: "111 58",
            country: "Sweden",
            vat_number: "SE987654321001",
            default_currency: "EUR",
            secondary_currency: "USD",
            secondary_currency_rate: "1.080000",
            secondary_currency_rate_source: "operator_manual",
            secondary_currency_rate_as_of: "2026-04-13T11:00:00.000Z",
            logo_file_key: null,
            brand_primary_color: "#F97316",
            brand_secondary_color: "#FDBA74",
            sidebar_background_color: "#1E293B",
            sidebar_text_color: "#F8FAFC",
            created_at: "2026-04-13T10:00:00.000Z",
            updated_at: "2026-04-13T11:00:00.000Z",
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("loads and saves tenant company settings", async () => {
        render(<CompanySettingsPage />);

        await waitFor(() => {
            expect(screen.getByDisplayValue("Northwind Workspace")).toBeTruthy();
        });

        fireEvent.change(screen.getByLabelText(/Company name/i), {
            target: { value: "Northwind CRM" },
        });
        fireEvent.change(screen.getByLabelText(/Address line 1/i), {
            target: { value: "Sveavagen 2" },
        });
        fireEvent.change(screen.getByLabelText(/Address line 2/i), {
            target: { value: "Floor 4" },
        });
        fireEvent.change(screen.getByLabelText(/Postal code/i), {
            target: { value: "111 58" },
        });
        fireEvent.change(screen.getByLabelText(/VAT \/ tax identifier/i), {
            target: { value: "SE987654321001" },
        });
        fireEvent.change(screen.getByLabelText(/Default currency/i), {
            target: { value: "eur" },
        });
        fireEvent.change(screen.getByLabelText(/^Secondary currency$/i), {
            target: { value: "usd" },
        });
        fireEvent.change(screen.getByLabelText(/Secondary currency rate/i), {
            target: { value: "1.080000" },
        });
        fireEvent.change(screen.getByLabelText(/Primary Color picker/i), {
            target: { value: "#f97316" },
        });
        expect((screen.getByLabelText(/^Primary Color$/i) as HTMLInputElement).value).toBe("#F97316");

        fireEvent.change(screen.getByLabelText(/^Secondary Color$/i), {
            target: { value: "#fdba74" },
        });
        fireEvent.change(screen.getByLabelText(/Sidebar Background Color picker/i), {
            target: { value: "#1e293b" },
        });
        expect((screen.getByLabelText(/^Sidebar Background Color$/i) as HTMLInputElement).value).toBe("#1E293B");

        fireEvent.change(screen.getByLabelText(/^Sidebar Text Color$/i), {
            target: { value: "#f8fafc" },
        });
        fireEvent.click(screen.getByRole("button", { name: /Save company settings/i }));

        await waitFor(() => {
            expect(mocks.updateCurrentTenant).toHaveBeenCalledWith(
                expect.objectContaining({
                    name: "Northwind CRM",
                    address_line_1: "Sveavagen 2",
                    address_line_2: "Floor 4",
                    postal_code: "111 58",
                    vat_number: "SE987654321001",
                    default_currency: "EUR",
                    secondary_currency: "USD",
                    secondary_currency_rate: "1.080000",
                    brand_primary_color: "#F97316",
                    brand_secondary_color: "#FDBA74",
                    sidebar_background_color: "#1E293B",
                    sidebar_text_color: "#F8FAFC",
                }),
            );
        });

        expect(screen.getByText(/Company settings saved\./i)).toBeTruthy();
        expect(screen.getByText(/Live preview/i)).toBeTruthy();
        expect(screen.getByText(/Source: Operator Manual/i)).toBeTruthy();
        expect(screen.getByRole("link", { name: /Manage logo/i })).toBeTruthy();
        expect((screen.getByLabelText(/^Primary Color$/i) as HTMLInputElement).value).toBe("#F97316");
        expect((screen.getByLabelText(/^Secondary Color$/i) as HTMLInputElement).value).toBe("#FDBA74");
        expect((screen.getByLabelText(/^Sidebar Background Color$/i) as HTMLInputElement).value).toBe("#1E293B");
        expect((screen.getByLabelText(/^Sidebar Text Color$/i) as HTMLInputElement).value).toBe("#F8FAFC");
    });
});

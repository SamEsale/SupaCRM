import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/services/tenants.service", () => ({
    getCurrentTenant: vi.fn(),
    updateCurrentTenant: vi.fn(),
    buildTenantUpdatePayload: vi.fn((tenant, overrides) => ({ ...tenant, ...overrides })),
}));

import SettingsPage from "@/app/(dashboard)/settings/page";
import CompanySettingsPage from "@/app/(dashboard)/settings/company/page";
import { getCurrentTenant } from "@/services/tenants.service";

const baseTenant = {
    id: "tenant-1",
    name: "Acme Workspace",
    is_active: true,
    status: "active" as const,
    status_reason: null,
    legal_name: "Acme AB",
    address_line_1: "Main Street 1",
    address_line_2: null,
    city: "Stockholm",
    state_region: null,
    postal_code: "111 22",
    country: "SE",
    vat_number: "SE123456789001",
    default_currency: "USD",
    secondary_currency: "EUR",
    secondary_currency_rate: "10.500000",
    secondary_currency_rate_source: "operator_manual",
    secondary_currency_rate_as_of: "2026-04-24T10:00:00.000Z",
    brand_primary_color: "#112233",
    brand_secondary_color: "#334455",
    sidebar_background_color: "#0F172A",
    sidebar_text_color: "#E2E8F0",
    logo_file_key: "tenants/tenant-1/logo.png",
    created_at: "2026-04-24T10:00:00.000Z",
    updated_at: "2026-04-24T10:00:00.000Z",
};

describe("settings pages", () => {
    beforeEach(() => {
        vi.mocked(getCurrentTenant).mockResolvedValue(baseTenant);
    });

    afterEach(() => {
        cleanup();
    });

    it("renders the settings overview with real tenant data", async () => {
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Settings" })).toBeTruthy();
        });

        expect(screen.getByText("Acme Workspace")).toBeTruthy();
        expect(screen.getByRole("link", { name: /company settings/i })).toBeTruthy();
        expect(screen.getByRole("link", { name: /branding/i })).toBeTruthy();
    });

    it("renders the company settings page with the tenant form fields", async () => {
        render(<CompanySettingsPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Company Settings" })).toBeTruthy();
        });

        expect(screen.getByDisplayValue("Acme Workspace")).toBeTruthy();
        expect(screen.getByDisplayValue("Acme AB")).toBeTruthy();
        expect(screen.getByDisplayValue("USD")).toBeTruthy();
    });
});

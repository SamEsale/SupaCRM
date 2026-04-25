import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/constants/env";

const mocks = vi.hoisted(() => ({
    getTenantBranding: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
        user: {
            email: "supacrm@test.com",
            tenant_id: "tenant-1",
        },
    }),
}));

vi.mock("next/navigation", () => ({
    usePathname: () => "/products",
}));

vi.mock("@/services/tenant-branding.service", () => ({
    getTenantBranding: mocks.getTenantBranding,
}));

vi.mock("@/components/auth/logout-button", () => ({
    default: () => <button type="button">Logout</button>,
}));

import DashboardShell from "@/components/layout/dashboard-shell";

beforeEach(() => {
    mocks.getTenantBranding.mockReset();
    mocks.getTenantBranding.mockResolvedValue({
        tenant_id: "tenant-1",
        logo_file_key: "tenant-logos/tenant-1/company-logo.png",
        logo_url: null,
        brand_primary_color: "#F97316",
        brand_secondary_color: "#FDBA74",
        sidebar_background_color: "#1E293B",
        sidebar_text_color: "#F8FAFC",
    });
});

afterEach(() => {
    cleanup();
});

describe("dashboard shell branding", () => {
    it("renders the tenant logo in both the header and sidebar brand areas", async () => {
        render(
            <DashboardShell>
                <div>Dashboard content</div>
            </DashboardShell>,
        );

        await waitFor(() => {
            expect(mocks.getTenantBranding).toHaveBeenCalledTimes(1);
        });

        const logos = await screen.findAllByAltText(/tenant logo/i);
        expect(logos).toHaveLength(2);
        expect((logos[0] as HTMLImageElement).src).toBe(
            new URL("/media/tenant-logos/tenant-1/company-logo.png", API_BASE_URL).toString(),
        );
        expect(document.documentElement.style.getPropertyValue("--brand-primary")).toBe("#F97316");
        expect(document.documentElement.style.getPropertyValue("--sidebar-bg")).toBe("#1E293B");
        expect(document.documentElement.style.getPropertyValue("--sidebar-text")).toBe("#F8FAFC");
    });

    it("falls back to initials when branding cannot be loaded", async () => {
        mocks.getTenantBranding.mockRejectedValueOnce(new Error("branding unavailable"));

        render(
            <DashboardShell>
                <div>Dashboard content</div>
            </DashboardShell>,
        );

        await waitFor(() => {
            expect(mocks.getTenantBranding).toHaveBeenCalledTimes(1);
        });

        expect(screen.getAllByText("SC")).toHaveLength(2);
        expect(screen.queryByAltText(/tenant logo/i)).toBeNull();
        expect(document.documentElement.style.getPropertyValue("--brand-primary")).toBe("#2563EB");
        expect(document.documentElement.style.getPropertyValue("--sidebar-bg")).toBe("#111827");
        expect(document.documentElement.style.getPropertyValue("--sidebar-text")).toBe("#FFFFFF");
    });

    it("refreshes the shell branding after a tenant branding change event", async () => {
        mocks.getTenantBranding
            .mockResolvedValueOnce({
                tenant_id: "tenant-1",
                logo_file_key: null,
                logo_url: null,
                brand_primary_color: "#2563EB",
                brand_secondary_color: "#1D4ED8",
                sidebar_background_color: "#111827",
                sidebar_text_color: "#FFFFFF",
            })
            .mockResolvedValueOnce({
                tenant_id: "tenant-1",
                logo_file_key: "tenant-logos/tenant-1/company-logo.png",
                logo_url: null,
                brand_primary_color: "#14B8A6",
                brand_secondary_color: "#0F766E",
                sidebar_background_color: "#0F172A",
                sidebar_text_color: "#E2E8F0",
            });

        render(
            <DashboardShell>
                <div>Dashboard content</div>
            </DashboardShell>,
        );

        await waitFor(() => {
            expect(screen.getAllByText("SC")).toHaveLength(2);
        });

        window.dispatchEvent(new Event("tenant-branding-changed"));

        await waitFor(() => {
            expect(mocks.getTenantBranding).toHaveBeenCalledTimes(2);
        });

        const logos = await screen.findAllByAltText(/tenant logo/i);
        expect(logos).toHaveLength(2);
        expect((logos[0] as HTMLImageElement).src).toBe(
            new URL("/media/tenant-logos/tenant-1/company-logo.png", API_BASE_URL).toString(),
        );
        expect(document.documentElement.style.getPropertyValue("--brand-primary")).toBe("#14B8A6");
        expect(document.documentElement.style.getPropertyValue("--sidebar-bg")).toBe("#0F172A");
        expect(document.documentElement.style.getPropertyValue("--sidebar-text")).toBe("#E2E8F0");
    });
});

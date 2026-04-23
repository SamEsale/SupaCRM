import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    pathname: "/settings/integrations",
    getMarketingIntegrations: vi.fn(),
    updateWhatsAppIntegration: vi.fn(),
    updateSmtpSettings: vi.fn(),
    testSmtpConnection: vi.fn(),
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

vi.mock("@/services/marketing-integrations.service", () => ({
    getMarketingIntegrations: mocks.getMarketingIntegrations,
    updateWhatsAppIntegration: mocks.updateWhatsAppIntegration,
    updateSmtpSettings: mocks.updateSmtpSettings,
    testSmtpConnection: mocks.testSmtpConnection,
}));

import SettingsIntegrationsPage from "@/app/(dashboard)/settings/integrations/page";

describe("settings integrations page", () => {
    beforeEach(() => {
        mocks.getMarketingIntegrations.mockReset();
        mocks.updateWhatsAppIntegration.mockReset();
        mocks.updateSmtpSettings.mockReset();
        mocks.testSmtpConnection.mockReset();

        mocks.getMarketingIntegrations.mockResolvedValue({
            whatsapp: {
                business_account_id: "wa-acc-1",
                phone_number_id: "pn-1",
                display_name: "SupaCRM Inbox",
                access_token_set: true,
                webhook_verify_token_set: true,
                is_enabled: true,
                updated_at: "2026-04-13T10:00:00.000Z",
            },
            smtp: {
                smtp_host: "smtp.example.com",
                smtp_port: 587,
                smtp_username: "mailer",
                from_email: "no-reply@example.com",
                from_name: "Growth Team",
                use_tls: true,
                use_ssl: false,
                password_set: true,
                is_enabled: true,
                updated_at: "2026-04-13T10:00:00.000Z",
            },
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders the real settings integrations surface and loads persisted communication settings", async () => {
        render(<SettingsIntegrationsPage />);

        await waitFor(() => {
            expect(mocks.getMarketingIntegrations).toHaveBeenCalledTimes(1);
        });

        expect(screen.getByRole("heading", { name: "Integrations", level: 1 })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "WhatsApp Business" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Bulk Email / SMTP" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Company" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Users & Roles" })).toBeTruthy();
    });
});

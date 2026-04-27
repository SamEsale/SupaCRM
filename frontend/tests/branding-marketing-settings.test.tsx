import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/constants/env";

const mocks = vi.hoisted(() => ({
    getTenantBranding: vi.fn(),
    updateTenantBranding: vi.fn(),
    uploadFileToStorage: vi.fn(),
    getMarketingIntegrations: vi.fn(),
    updateWhatsAppIntegration: vi.fn(),
    updateSmtpSettings: vi.fn(),
    testSmtpConnection: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("@/services/tenant-branding.service", () => ({
    getTenantBranding: mocks.getTenantBranding,
    updateTenantBranding: mocks.updateTenantBranding,
}));

vi.mock("@/services/uploads.service", () => ({
    uploadFileToStorage: mocks.uploadFileToStorage,
}));

vi.mock("@/services/marketing-integrations.service", () => ({
    getMarketingIntegrations: mocks.getMarketingIntegrations,
    updateWhatsAppIntegration: mocks.updateWhatsAppIntegration,
    updateSmtpSettings: mocks.updateSmtpSettings,
    testSmtpConnection: mocks.testSmtpConnection,
}));

import BrandingLogoCard from "@/components/settings/BrandingLogoCard";
import MarketingIntegrationsForm from "@/components/marketing/MarketingIntegrationsForm";

beforeEach(() => {
    mocks.getTenantBranding.mockReset();
    mocks.updateTenantBranding.mockReset();
    mocks.uploadFileToStorage.mockReset();
    mocks.getMarketingIntegrations.mockReset();
    mocks.updateWhatsAppIntegration.mockReset();
    mocks.updateSmtpSettings.mockReset();
    mocks.testSmtpConnection.mockReset();

    mocks.getTenantBranding.mockResolvedValue({
        tenant_id: "tenant-1",
        logo_file_key: null,
        logo_url: null,
        brand_primary_color: null,
        brand_secondary_color: null,
        sidebar_background_color: null,
        sidebar_text_color: null,
    });
    mocks.updateTenantBranding
        .mockResolvedValueOnce({
            tenant_id: "tenant-1",
            logo_file_key: "tenant-logos/tenant-1/company-logo.png",
            logo_url: null,
            brand_primary_color: null,
            brand_secondary_color: null,
            sidebar_background_color: null,
            sidebar_text_color: null,
        })
        .mockResolvedValueOnce({
            tenant_id: "tenant-1",
            logo_file_key: null,
            logo_url: null,
            brand_primary_color: null,
            brand_secondary_color: null,
            sidebar_background_color: null,
            sidebar_text_color: null,
        });
    mocks.uploadFileToStorage.mockResolvedValue({
        bucket: "supacrm",
        file_key: "tenant-logos/tenant-1/company-logo.png",
        file_url: null,
    });
    mocks.getMarketingIntegrations.mockResolvedValue({
        whatsapp: {
            business_account_id: null,
            phone_number_id: null,
            display_name: null,
            access_token_set: false,
            webhook_verify_token_set: false,
            is_enabled: false,
            updated_at: null,
        },
        smtp: {
            smtp_host: null,
            smtp_port: 587,
            smtp_username: null,
            from_email: null,
            from_name: null,
            use_tls: true,
            use_ssl: false,
            password_set: false,
            is_enabled: false,
            updated_at: null,
        },
    });
    mocks.updateWhatsAppIntegration.mockResolvedValue({
        business_account_id: "123",
        phone_number_id: "456",
        display_name: "SupaCRM",
        access_token_set: true,
        webhook_verify_token_set: true,
        is_enabled: true,
        updated_at: new Date().toISOString(),
    });
    mocks.updateSmtpSettings.mockResolvedValue({
        smtp_host: "smtp.example.com",
        smtp_port: 587,
        smtp_username: "mailer",
        from_email: "no-reply@example.com",
        from_name: "Growth Team",
        use_tls: true,
        use_ssl: false,
        password_set: true,
        is_enabled: true,
        updated_at: new Date().toISOString(),
    });
    mocks.testSmtpConnection.mockResolvedValue({
        success: true,
        message: "SMTP connection succeeded",
    });
});

afterEach(() => {
    cleanup();
});

describe("branding and marketing settings", () => {
    it("uploads and removes a company logo through the settings surface", async () => {
        render(<BrandingLogoCard />);

        await waitFor(() => {
            expect(screen.getByText(/No logo uploaded yet\./i)).toBeTruthy();
        });

        const uploadInput = screen.getByLabelText(/upload company logo/i);
        const selectedFile = new File(["logo-bytes"], "logo.png", { type: "image/png" });
        fireEvent.change(uploadInput, {
            target: { files: [selectedFile] },
        });

        await waitFor(() => {
            expect(mocks.uploadFileToStorage).toHaveBeenCalledTimes(1);
        });
        expect(mocks.uploadFileToStorage).toHaveBeenCalledWith(
            selectedFile,
            "tenant-logo",
        );
        await waitFor(() => {
            expect(mocks.updateTenantBranding).toHaveBeenCalledWith({
                logo_file_key: "tenant-logos/tenant-1/company-logo.png",
            });
        });

        await waitFor(() => {
            expect(screen.getByAltText(/tenant logo preview/i)).toBeTruthy();
        });
        expect((screen.getByAltText(/tenant logo preview/i) as HTMLImageElement).src).toBe(
            new URL(
                "/media/tenant-logos/tenant-1/company-logo.png",
                API_BASE_URL,
            ).toString(),
        );

        fireEvent.click(screen.getByRole("button", { name: /remove logo/i }));

        await waitFor(() => {
            expect(mocks.updateTenantBranding).toHaveBeenCalledWith({
                logo_file_key: null,
            });
        });
        await waitFor(() => {
            expect(screen.getByText(/No logo uploaded yet\./i)).toBeTruthy();
        });
    });

    it("saves WhatsApp and SMTP settings and can test SMTP connection", async () => {
        render(<MarketingIntegrationsForm />);

        await waitFor(() => {
            expect(mocks.getMarketingIntegrations).toHaveBeenCalledTimes(1);
        });

        fireEvent.change(screen.getByPlaceholderText(/business account id/i), {
            target: { value: "123" },
        });
        fireEvent.change(screen.getByPlaceholderText(/phone number id/i), {
            target: { value: "456" },
        });
        fireEvent.change(screen.getByPlaceholderText(/display name/i), {
            target: { value: "SupaCRM" },
        });
        fireEvent.change(screen.getByPlaceholderText(/access token/i), {
            target: { value: "secret-access-token" },
        });
        fireEvent.change(screen.getByPlaceholderText(/webhook verify token/i), {
            target: { value: "verify-token" },
        });
        fireEvent.click(screen.getByLabelText(/whatsapp enabled/i));
        fireEvent.click(screen.getByRole("button", { name: /save whatsapp settings/i }));

        await waitFor(() => {
            expect(mocks.updateWhatsAppIntegration).toHaveBeenCalledWith(
                expect.objectContaining({
                    business_account_id: "123",
                    phone_number_id: "456",
                    display_name: "SupaCRM",
                    access_token: "secret-access-token",
                    webhook_verify_token: "verify-token",
                    is_enabled: true,
                }),
            );
        });

        fireEvent.change(screen.getByPlaceholderText(/smtp host/i), {
            target: { value: "smtp.example.com" },
        });
        fireEvent.change(screen.getByPlaceholderText(/smtp port/i), {
            target: { value: "587" },
        });
        fireEvent.change(screen.getByPlaceholderText(/smtp username/i), {
            target: { value: "mailer" },
        });
        fireEvent.change(screen.getByPlaceholderText(/from name/i), {
            target: { value: "Growth Team" },
        });
        fireEvent.change(screen.getByPlaceholderText(/from address/i), {
            target: { value: "no-reply@example.com" },
        });
        fireEvent.change(screen.getByPlaceholderText(/smtp password/i), {
            target: { value: "secret-password" },
        });
        fireEvent.click(screen.getAllByLabelText(/Use TLS/i)[0]);
        fireEvent.click(screen.getByRole("button", { name: /save smtp settings/i }));

        await waitFor(() => {
            expect(mocks.updateSmtpSettings).toHaveBeenCalledWith(
                expect.objectContaining({
                    smtp_host: "smtp.example.com",
                    smtp_port: 587,
                    smtp_username: "mailer",
                    smtp_password: "secret-password",
                    from_email: "no-reply@example.com",
                    from_name: "Growth Team",
                    use_tls: false,
                    use_ssl: false,
                    is_enabled: false,
                }),
            );
        });

        fireEvent.click(screen.getByRole("button", { name: /test connection/i }));

        await waitFor(() => {
            expect(mocks.testSmtpConnection).toHaveBeenCalledTimes(1);
        });
        expect(screen.getByText(/smtp connection succeeded/i)).toBeTruthy();
    });
});

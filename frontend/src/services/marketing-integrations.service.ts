import { apiClient } from "@/lib/api-client";
import type {
    MarketingIntegrations,
    SmtpSettings,
    SmtpSettingsUpdateRequest,
    WhatsAppIntegrationSettings,
    WhatsAppIntegrationUpdateRequest,
} from "@/types/settings";

export async function getMarketingIntegrations(): Promise<MarketingIntegrations> {
    const response = await apiClient.get<MarketingIntegrations>("/marketing/integrations");
    return response.data;
}

export async function updateWhatsAppIntegration(
    payload: WhatsAppIntegrationUpdateRequest,
): Promise<WhatsAppIntegrationSettings> {
    const response = await apiClient.put<WhatsAppIntegrationSettings>(
        "/marketing/integrations/whatsapp",
        payload,
    );
    return response.data;
}

export async function updateSmtpSettings(
    payload: SmtpSettingsUpdateRequest,
): Promise<SmtpSettings> {
    const response = await apiClient.put<SmtpSettings>("/marketing/integrations/smtp", payload);
    return response.data;
}

export async function testSmtpConnection(): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post<{ success: boolean; message: string }>(
        "/marketing/integrations/smtp/test",
    );
    return response.data;
}


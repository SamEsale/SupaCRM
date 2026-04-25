export interface TenantBranding {
    tenant_id: string;
    logo_file_key: string | null;
    logo_url: string | null;
    brand_primary_color: string | null;
    brand_secondary_color: string | null;
    sidebar_background_color: string | null;
    sidebar_text_color: string | null;
}

export interface TenantBrandingUpdateRequest {
    logo_file_key: string | null;
}

export interface WhatsAppIntegrationSettings {
    business_account_id: string | null;
    phone_number_id: string | null;
    display_name: string | null;
    access_token_set: boolean;
    webhook_verify_token_set: boolean;
    is_enabled: boolean;
    updated_at: string | null;
}

export interface WhatsAppIntegrationUpdateRequest {
    business_account_id: string | null;
    phone_number_id: string | null;
    display_name: string | null;
    access_token: string | null;
    webhook_verify_token: string | null;
    is_enabled: boolean;
}

export interface SmtpSettings {
    smtp_host: string | null;
    smtp_port: number;
    smtp_username: string | null;
    from_email: string | null;
    from_name: string | null;
    use_tls: boolean;
    use_ssl: boolean;
    password_set: boolean;
    is_enabled: boolean;
    updated_at: string | null;
}

export interface SmtpSettingsUpdateRequest {
    smtp_host: string | null;
    smtp_port: number;
    smtp_username: string | null;
    smtp_password: string | null;
    from_email: string | null;
    from_name: string | null;
    use_tls: boolean;
    use_ssl: boolean;
    is_enabled: boolean;
}

export interface MarketingIntegrations {
    whatsapp: WhatsAppIntegrationSettings;
    smtp: SmtpSettings;
}

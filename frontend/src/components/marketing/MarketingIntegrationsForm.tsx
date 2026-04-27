"use client";

import { useEffect, useState } from "react";

import { useToast } from "@/components/feedback/ToastProvider";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-errors";
import {
    getMarketingIntegrations,
    testSmtpConnection,
    updateSmtpSettings,
    updateWhatsAppIntegration,
} from "@/services/marketing-integrations.service";
import type {
    MarketingIntegrations,
    SmtpSettings,
    WhatsAppIntegrationSettings,
} from "@/types/settings";

const DEFAULT_WHATSAPP: WhatsAppIntegrationSettings = {
    business_account_id: null,
    phone_number_id: null,
    display_name: null,
    access_token_set: false,
    webhook_verify_token_set: false,
    is_enabled: false,
    updated_at: null,
};

const DEFAULT_SMTP: SmtpSettings = {
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
};

export default function MarketingIntegrationsForm() {
    const auth = useAuth();
    const toast = useToast();
    const [whatsapp, setWhatsApp] = useState<WhatsAppIntegrationSettings>(DEFAULT_WHATSAPP);
    const [smtp, setSmtp] = useState<SmtpSettings>(DEFAULT_SMTP);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isSavingWhatsApp, setIsSavingWhatsApp] = useState<boolean>(false);
    const [isSavingSmtp, setIsSavingSmtp] = useState<boolean>(false);
    const [isTestingSmtp, setIsTestingSmtp] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [smtpTestMessage, setSmtpTestMessage] = useState<string>("");
    const [smtpSecret, setSmtpSecret] = useState<string>("");
    const [whatsappAccessToken, setWhatsAppAccessToken] = useState<string>("");
    const [whatsappVerifyToken, setWhatsAppVerifyToken] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadSettings(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                const settings: MarketingIntegrations = await getMarketingIntegrations();
                if (!isMounted) {
                    return;
                }

                setWhatsApp(settings.whatsapp);
                setSmtp(settings.smtp);
                setSmtpSecret("");
                setWhatsAppAccessToken("");
                setWhatsAppVerifyToken("");
            } catch (error) {
                console.error("Failed to load marketing integrations:", error);
                if (isMounted) {
                    setErrorMessage(getApiErrorMessage(error, "Failed to load integrations."));
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadSettings();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    async function handleSaveWhatsApp(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();
        try {
            setIsSavingWhatsApp(true);
            setErrorMessage("");
            setSuccessMessage("");
            const updated = await updateWhatsAppIntegration({
                business_account_id: whatsapp.business_account_id?.trim() || null,
                phone_number_id: whatsapp.phone_number_id?.trim() || null,
                display_name: whatsapp.display_name?.trim() || null,
                access_token: whatsappAccessToken.trim() || null,
                webhook_verify_token: whatsappVerifyToken.trim() || null,
                is_enabled: whatsapp.is_enabled,
            });
            setWhatsApp(updated);
            setWhatsAppAccessToken("");
            setWhatsAppVerifyToken("");
            const message = "WhatsApp integration saved.";
            setSuccessMessage(message);
            toast.success(message);
        } catch (error) {
            console.error("Failed to save WhatsApp integration:", error);
            const message = getApiErrorMessage(error, "Failed to save integrations.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setIsSavingWhatsApp(false);
        }
    }

    async function handleSaveSmtp(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();
        try {
            setIsSavingSmtp(true);
            setErrorMessage("");
            setSuccessMessage("");
            const updated = await updateSmtpSettings({
                smtp_host: smtp.smtp_host?.trim() || null,
                smtp_port: smtp.smtp_port,
                smtp_username: smtp.smtp_username?.trim() || null,
                smtp_password: smtpSecret.trim() || null,
                from_email: smtp.from_email?.trim() || null,
                from_name: smtp.from_name?.trim() || null,
                use_tls: smtp.use_tls,
                use_ssl: smtp.use_ssl,
                is_enabled: smtp.is_enabled,
            });
            setSmtp(updated);
            setSmtpSecret("");
            const message = "SMTP settings saved.";
            setSuccessMessage(message);
            toast.success(message);
        } catch (error) {
            console.error("Failed to save SMTP settings:", error);
            const message = getApiErrorMessage(error, "Failed to save integrations.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setIsSavingSmtp(false);
        }
    }

    async function handleTestSmtp(): Promise<void> {
        try {
            setIsTestingSmtp(true);
            setErrorMessage("");
            setSuccessMessage("");
            const result = await testSmtpConnection();
            setSmtpTestMessage(result.message);
            toast.success(result.message);
        } catch (error) {
            console.error("Failed to test SMTP connection:", error);
            setSmtpTestMessage("");
            const message = getApiErrorMessage(error, "Failed to save integrations.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setIsTestingSmtp(false);
        }
    }

    return (
        <section className="space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-slate-900">WhatsApp Business</h2>
                <p className="mt-1 text-sm text-slate-600">
                    Store the operational WhatsApp Business configuration used by the CRM/marketing layer.
                </p>
                <p className="mt-2 text-xs text-slate-500">
                    This launch slice stores tenant-scoped configuration and intake context only. It does not claim a live provider connection.
                </p>

                <form className="mt-4 space-y-4" onSubmit={handleSaveWhatsApp}>
                    <div className="grid gap-4 md:grid-cols-2">
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="Business account ID"
                            value={whatsapp.business_account_id ?? ""}
                            onChange={(event) =>
                                setWhatsApp((current) => ({
                                    ...current,
                                    business_account_id: event.target.value,
                                }))
                            }
                        />
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="Phone number ID"
                            value={whatsapp.phone_number_id ?? ""}
                            onChange={(event) =>
                                setWhatsApp((current) => ({
                                    ...current,
                                    phone_number_id: event.target.value,
                                }))
                            }
                        />
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="Display name"
                            value={whatsapp.display_name ?? ""}
                            onChange={(event) =>
                                setWhatsApp((current) => ({
                                    ...current,
                                    display_name: event.target.value,
                                }))
                            }
                        />
                        <label className="flex items-center gap-2 text-sm text-slate-700">
                            <input
                                type="checkbox"
                                checked={whatsapp.is_enabled}
                                onChange={(event) =>
                                    setWhatsApp((current) => ({
                                        ...current,
                                        is_enabled: event.target.checked,
                                    }))
                                }
                            />
                            WhatsApp enabled
                        </label>
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            type="password"
                            placeholder={
                                whatsapp.access_token_set ? "Access token is already set" : "Access token"
                            }
                            value={whatsappAccessToken}
                            onChange={(event) => setWhatsAppAccessToken(event.target.value)}
                        />
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            type="password"
                            placeholder={
                                whatsapp.webhook_verify_token_set
                                    ? "Webhook verify token is already set"
                                    : "Webhook verify token"
                            }
                            value={whatsappVerifyToken}
                            onChange={(event) => setWhatsAppVerifyToken(event.target.value)}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading || isSavingWhatsApp}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSavingWhatsApp ? "Saving..." : "Save WhatsApp settings"}
                    </button>
                </form>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-slate-900">Bulk Email / SMTP</h2>
                <p className="mt-1 text-sm text-slate-600">
                    Configure outbound email delivery for transactional and bulk email workflows.
                </p>
                <p className="mt-2 text-xs text-slate-500">
                    Secrets stay masked after save. Enter a new password only when you want to rotate it.
                </p>

                <form className="mt-4 space-y-4" onSubmit={handleSaveSmtp}>
                    <div className="grid gap-4 md:grid-cols-2">
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="SMTP host"
                            value={smtp.smtp_host ?? ""}
                            onChange={(event) =>
                                setSmtp((current) => ({
                                    ...current,
                                    smtp_host: event.target.value,
                                }))
                            }
                        />
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            type="number"
                            min={1}
                            max={65535}
                            placeholder="SMTP port"
                            value={smtp.smtp_port}
                            onChange={(event) =>
                                setSmtp((current) => ({
                                    ...current,
                                    smtp_port: Number(event.target.value || 0),
                                }))
                            }
                        />
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="SMTP username"
                            value={smtp.smtp_username ?? ""}
                            onChange={(event) =>
                                setSmtp((current) => ({
                                    ...current,
                                    smtp_username: event.target.value,
                                }))
                            }
                        />
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="From name"
                            value={smtp.from_name ?? ""}
                            onChange={(event) =>
                                setSmtp((current) => ({
                                    ...current,
                                    from_name: event.target.value,
                                }))
                            }
                        />
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="From address"
                            value={smtp.from_email ?? ""}
                            onChange={(event) =>
                                setSmtp((current) => ({
                                    ...current,
                                    from_email: event.target.value,
                                }))
                            }
                        />
                        <input
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            type="password"
                            placeholder={smtp.password_set ? "Password is already set" : "SMTP password"}
                            value={smtpSecret}
                            onChange={(event) => setSmtpSecret(event.target.value)}
                        />
                        <div className="flex flex-wrap items-center gap-4 text-sm text-slate-700">
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={smtp.use_tls}
                                    onChange={(event) =>
                                        setSmtp((current) => ({
                                            ...current,
                                            use_tls: event.target.checked,
                                        }))
                                    }
                                />
                                Use TLS
                            </label>
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={smtp.use_ssl}
                                    onChange={(event) =>
                                        setSmtp((current) => ({
                                            ...current,
                                            use_ssl: event.target.checked,
                                        }))
                                    }
                                />
                                Use SSL
                            </label>
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={smtp.is_enabled}
                                    onChange={(event) =>
                                        setSmtp((current) => ({
                                            ...current,
                                            is_enabled: event.target.checked,
                                        }))
                                    }
                                />
                                SMTP enabled
                            </label>
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        <button
                            type="submit"
                            disabled={isLoading || isSavingSmtp}
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isSavingSmtp ? "Saving..." : "Save SMTP settings"}
                        </button>
                        <button
                            type="button"
                            onClick={() => void handleTestSmtp()}
                            disabled={isLoading || isSavingSmtp || isTestingSmtp}
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isTestingSmtp ? "Testing..." : "Test connection"}
                        </button>
                    </div>
                </form>
            </div>

            {errorMessage ? (
                <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {errorMessage}
                </p>
            ) : null}
            {successMessage ? (
                <p className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
                    {successMessage}
                </p>
            ) : null}
            {smtpTestMessage ? (
                <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    {smtpTestMessage}
                </p>
            ) : null}
        </section>
    );
}

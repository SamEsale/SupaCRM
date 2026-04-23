"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/feedback/ToastProvider";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-errors";
import {
    getPaymentGatewaySettings,
    getPaymentProviderFoundation,
    updatePaymentGatewayProvider,
} from "@/services/payments.service";
import type {
    PaymentGatewayMode,
    PaymentGatewayProvider,
    PaymentGatewayProviderSettings,
    PaymentGatewaySettingsSnapshot,
    PaymentProviderFoundation,
    PaymentProviderFoundationSnapshot,
} from "@/types/payments";

type ProviderFormState = {
    is_enabled: boolean;
    is_default: boolean;
    mode: PaymentGatewayMode;
    account_id: string;
    merchant_id: string;
    publishable_key: string;
    client_id: string;
    secret_key: string;
    api_key: string;
    client_secret: string;
    webhook_secret: string;
};

type ProviderFormMap = Record<PaymentGatewayProvider, ProviderFormState>;

type EditableFieldKey =
    | "account_id"
    | "merchant_id"
    | "publishable_key"
    | "client_id"
    | "secret_key"
    | "api_key"
    | "client_secret"
    | "webhook_secret";

const PROVIDER_FIELDS: Record<
    PaymentGatewayProvider,
    Array<{ key: EditableFieldKey; label: string; placeholder: string; helper: string }>
> = {
    stripe: [
        {
            key: "publishable_key",
            label: "Publishable key",
            placeholder: "pk_test_...",
            helper: "Safe to display in operator views when needed.",
        },
        {
            key: "secret_key",
            label: "Secret key",
            placeholder: "Leave blank to keep the saved secret",
            helper: "Used server-side for Stripe billing operations.",
        },
        {
            key: "webhook_secret",
            label: "Webhook secret",
            placeholder: "Leave blank to keep the saved webhook secret",
            helper: "Used to verify incoming Stripe commercial events.",
        },
    ],
    revolut_business: [
        {
            key: "merchant_id",
            label: "Merchant ID",
            placeholder: "Merchant ID",
            helper: "Stored for operator readiness only in this slice.",
        },
        {
            key: "api_key",
            label: "API key",
            placeholder: "Leave blank to keep the saved API key",
            helper: "Stored tenant-scoped, without claiming live automation.",
        },
        {
            key: "webhook_secret",
            label: "Webhook secret",
            placeholder: "Leave blank to keep the saved webhook secret",
            helper: "Stored for future provider expansion.",
        },
    ],
    payoneer: [
        {
            key: "account_id",
            label: "Account ID",
            placeholder: "Account ID",
            helper: "Stored tenant-scoped for operator visibility.",
        },
        {
            key: "client_id",
            label: "Client ID",
            placeholder: "Client ID",
            helper: "Used for provider identification only in this slice.",
        },
        {
            key: "client_secret",
            label: "Client secret",
            placeholder: "Leave blank to keep the saved client secret",
            helper: "Stored without claiming active Payoneer automation.",
        },
        {
            key: "webhook_secret",
            label: "Webhook secret",
            placeholder: "Leave blank to keep the saved webhook secret",
            helper: "Stored for future provider expansion.",
        },
    ],
};

function emptyProviderForm(): ProviderFormState {
    return {
        is_enabled: false,
        is_default: false,
        mode: "test",
        account_id: "",
        merchant_id: "",
        publishable_key: "",
        client_id: "",
        secret_key: "",
        api_key: "",
        client_secret: "",
        webhook_secret: "",
    };
}

function createInitialFormMap(): ProviderFormMap {
    return {
        stripe: emptyProviderForm(),
        revolut_business: emptyProviderForm(),
        payoneer: emptyProviderForm(),
    };
}

function buildProviderForms(snapshot: PaymentGatewaySettingsSnapshot): ProviderFormMap {
    const next = createInitialFormMap();

    snapshot.providers.forEach((provider) => {
        next[provider.provider] = {
            is_enabled: provider.is_enabled,
            is_default: provider.is_default,
            mode: provider.mode,
            account_id: provider.account_id ?? "",
            merchant_id: provider.merchant_id ?? "",
            publishable_key: provider.publishable_key ?? "",
            client_id: provider.client_id ?? "",
            secret_key: "",
            api_key: "",
            client_secret: "",
            webhook_secret: "",
        };
    });

    return next;
}

function formatLabel(value: string): string {
    return value
        .split("_")
        .join(" ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDateTime(value: string | null): string {
    if (!value) {
        return "Not saved yet";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }

    return parsed.toLocaleString("en-US");
}

function stateBadgeClass(state: PaymentProviderFoundation["foundation_state"]): string {
    if (state === "ready") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (state === "manual_only") {
        return "bg-amber-100 text-amber-900";
    }
    if (state === "needs_configuration") {
        return "bg-blue-100 text-blue-800";
    }
    return "bg-slate-100 text-slate-700";
}

export default function PaymentGatewaySettingsPage() {
    const auth = useAuth();
    const toast = useToast();
    const [settingsSnapshot, setSettingsSnapshot] = useState<PaymentGatewaySettingsSnapshot | null>(null);
    const [foundationSnapshot, setFoundationSnapshot] = useState<PaymentProviderFoundationSnapshot | null>(null);
    const [forms, setForms] = useState<ProviderFormMap>(createInitialFormMap());
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [savingProvider, setSavingProvider] = useState<PaymentGatewayProvider | "">("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadWorkspace(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                const [nextSettings, nextFoundation] = await Promise.all([
                    getPaymentGatewaySettings(),
                    getPaymentProviderFoundation(),
                ]);

                if (!isMounted) {
                    return;
                }

                setSettingsSnapshot(nextSettings);
                setFoundationSnapshot(nextFoundation);
                setForms(buildProviderForms(nextSettings));
            } catch (error) {
                console.error("Failed to load payment gateway settings:", error);
                if (isMounted) {
                    setErrorMessage(
                        getApiErrorMessage(
                            error,
                            "The payment gateway settings workspace could not be loaded.",
                        ),
                    );
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadWorkspace();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    const foundationByProvider = useMemo(() => {
        return new Map(
            (foundationSnapshot?.providers ?? []).map((provider) => [provider.provider, provider]),
        );
    }, [foundationSnapshot]);

    async function reloadWorkspace(): Promise<void> {
        const [nextSettings, nextFoundation] = await Promise.all([
            getPaymentGatewaySettings(),
            getPaymentProviderFoundation(),
        ]);
        setSettingsSnapshot(nextSettings);
        setFoundationSnapshot(nextFoundation);
        setForms(buildProviderForms(nextSettings));
    }

    async function handleSave(provider: PaymentGatewayProvider): Promise<void> {
        try {
            setSavingProvider(provider);
            setErrorMessage("");

            const form = forms[provider];
            await updatePaymentGatewayProvider(provider, {
                is_enabled: form.is_enabled,
                is_default: form.is_default,
                mode: form.mode,
                account_id: form.account_id.trim() || null,
                merchant_id: form.merchant_id.trim() || null,
                publishable_key: form.publishable_key.trim() || null,
                client_id: form.client_id.trim() || null,
                secret_key: form.secret_key.trim() || null,
                api_key: form.api_key.trim() || null,
                client_secret: form.client_secret.trim() || null,
                webhook_secret: form.webhook_secret.trim() || null,
            });

            await reloadWorkspace();
            toast.success(`${formatLabel(provider)} settings saved.`);
        } catch (error) {
            console.error("Failed to save payment gateway settings:", error);
            const message = getApiErrorMessage(error, "Failed to save payment gateway settings.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setSavingProvider("");
        }
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                            Payments
                        </p>
                        <h1 className="mt-2 text-3xl font-bold text-slate-900">Gateway Settings</h1>
                        <p className="mt-2 max-w-3xl text-sm text-slate-600">
                            Store tenant-scoped gateway credentials and operating mode without claiming a live provider connection unless the product actually supports it.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/finance/payments"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Transactions
                        </Link>
                        <Link
                            href="/finance/payments/integrations"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Provider Foundation
                        </Link>
                        <Link
                            href="/finance/payments/subscription-billing"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Subscription Billing
                        </Link>
                    </div>
                </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm text-slate-700">
                    Leaving secret fields blank preserves what is already stored. Saved secrets remain masked in the UI, and this page only manages operator configuration state.
                </p>
            </section>

            {errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {errorMessage}
                </section>
            ) : null}

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading gateway settings</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching tenant-scoped gateway configuration and provider foundation status.
                    </p>
                </section>
            ) : null}

            {!isLoading && settingsSnapshot ? (
                settingsSnapshot.providers.map((provider) => {
                    const foundation = foundationByProvider.get(provider.provider);
                    const form = forms[provider.provider];
                    const isSaving = savingProvider === provider.provider;

                    return (
                        <section
                            key={provider.provider}
                            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
                        >
                            <div className="flex flex-wrap items-start justify-between gap-4">
                                <div>
                                    <div className="flex flex-wrap items-center gap-2">
                                        <h2 className="text-2xl font-semibold text-slate-900">
                                            {provider.display_name}
                                        </h2>
                                        <span
                                            className={`rounded-full px-2.5 py-1 text-xs font-medium ${stateBadgeClass(
                                                foundation?.foundation_state ?? "disabled",
                                            )}`}
                                        >
                                            {formatLabel(foundation?.foundation_state ?? "disabled")}
                                        </span>
                                        {provider.is_default ? (
                                            <span className="rounded-full bg-slate-900 px-2.5 py-1 text-xs font-medium text-white">
                                                Default
                                            </span>
                                        ) : null}
                                    </div>
                                    <p className="mt-2 max-w-3xl text-sm text-slate-600">
                                        {foundation?.operator_summary ?? "No provider foundation summary is available yet."}
                                    </p>
                                    <p className="mt-2 text-xs text-slate-500">
                                        Last updated: {formatDateTime(provider.updated_at)}
                                    </p>
                                </div>

                                <div className="grid gap-2 text-sm text-slate-600">
                                    <span>Configuration: {formatLabel(provider.configuration_state)}</span>
                                    <span>Mode: {formatLabel(provider.mode)}</span>
                                    <span>Enabled: {provider.is_enabled ? "Yes" : "No"}</span>
                                </div>
                            </div>

                            <div className="mt-6 grid gap-4 md:grid-cols-3">
                                <label className="rounded-xl border border-slate-200 p-4 text-sm text-slate-700">
                                    <span className="font-medium text-slate-900">Enabled for this tenant</span>
                                    <input
                                        type="checkbox"
                                        className="mt-3 h-4 w-4 rounded border-slate-300"
                                        checked={form.is_enabled}
                                        onChange={(event) =>
                                            setForms((current) => ({
                                                ...current,
                                                [provider.provider]: {
                                                    ...current[provider.provider],
                                                    is_enabled: event.target.checked,
                                                },
                                            }))
                                        }
                                    />
                                </label>

                                <label className="rounded-xl border border-slate-200 p-4 text-sm text-slate-700">
                                    <span className="font-medium text-slate-900">Default provider</span>
                                    <input
                                        type="checkbox"
                                        className="mt-3 h-4 w-4 rounded border-slate-300"
                                        checked={form.is_default}
                                        onChange={(event) =>
                                            setForms((current) => ({
                                                ...current,
                                                [provider.provider]: {
                                                    ...current[provider.provider],
                                                    is_default: event.target.checked,
                                                },
                                            }))
                                        }
                                    />
                                </label>

                                <label className="rounded-xl border border-slate-200 p-4 text-sm text-slate-700">
                                    <span className="mb-2 block font-medium text-slate-900">Operating mode</span>
                                    <select
                                        value={form.mode}
                                        onChange={(event) =>
                                            setForms((current) => ({
                                                ...current,
                                                [provider.provider]: {
                                                    ...current[provider.provider],
                                                    mode: event.target.value as PaymentGatewayMode,
                                                },
                                            }))
                                        }
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                    >
                                        <option value="test">Test</option>
                                        <option value="live">Live</option>
                                    </select>
                                </label>
                            </div>

                            <div className="mt-6 grid gap-4 md:grid-cols-2">
                                {PROVIDER_FIELDS[provider.provider].map((field) => (
                                    <label key={field.key} className="block">
                                        <span className="mb-1 block text-sm font-medium text-slate-700">
                                            {field.label}
                                        </span>
                                        <input
                                            value={form[field.key]}
                                            onChange={(event) =>
                                                setForms((current) => ({
                                                    ...current,
                                                    [provider.provider]: {
                                                        ...current[provider.provider],
                                                        [field.key]: event.target.value,
                                                    },
                                                }))
                                            }
                                            placeholder={field.placeholder}
                                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                        />
                                        <span className="mt-1 block text-xs text-slate-500">
                                            {field.helper}
                                        </span>
                                    </label>
                                ))}
                            </div>

                            <div className="mt-6 grid gap-3 md:grid-cols-4">
                                <SecretState label="Secret key saved" active={provider.secret_key_set} />
                                <SecretState label="API key saved" active={provider.api_key_set} />
                                <SecretState label="Client secret saved" active={provider.client_secret_set} />
                                <SecretState label="Webhook secret saved" active={provider.webhook_secret_set} />
                            </div>

                            {provider.validation_errors.length > 0 ? (
                                <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                                    {provider.validation_errors.join(" ")}
                                </div>
                            ) : null}

                            <div className="mt-6 flex flex-wrap gap-3">
                                <button
                                    type="button"
                                    disabled={isSaving}
                                    onClick={() => {
                                        void handleSave(provider.provider);
                                    }}
                                    className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {isSaving ? "Saving..." : `Save ${provider.display_name}`}
                                </button>
                                <Link
                                    href="/finance/payments/integrations"
                                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                >
                                    Review provider foundation
                                </Link>
                            </div>
                        </section>
                    );
                })
            ) : null}
        </main>
    );
}

function SecretState({ label, active }: { label: string; active: boolean }) {
    return (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
            <p className="mt-2 text-sm font-medium text-slate-900">{active ? "Stored" : "Not stored"}</p>
        </div>
    );
}

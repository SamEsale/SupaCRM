"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/feedback/ToastProvider";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-errors";
import { resolveTenantTheme } from "@/lib/tenant-theme";
import { notifyTenantBrandingChanged } from "@/services/tenant-branding-events";
import {
    getCurrentTenant,
    updateCurrentTenant,
} from "@/services/tenants.service";
import type { Tenant, TenantUpdateRequest } from "@/types/tenants";

type CompanySettingsFormState = Omit<TenantUpdateRequest, "secondary_currency_rate"> & {
    secondary_currency_rate: string;
    secondary_currency_rate_source: string | null;
    secondary_currency_rate_as_of: string | null;
};

type BrandColorField =
    | "brand_primary_color"
    | "brand_secondary_color"
    | "sidebar_background_color"
    | "sidebar_text_color";

const DEFAULT_FORM_STATE: CompanySettingsFormState = {
    name: "",
    legal_name: null,
    address_line_1: null,
    address_line_2: null,
    city: null,
    state_region: null,
    postal_code: null,
    country: null,
    vat_number: null,
    default_currency: "USD",
    secondary_currency: null,
    secondary_currency_rate: "",
    secondary_currency_rate_source: null,
    secondary_currency_rate_as_of: null,
    brand_primary_color: null,
    brand_secondary_color: null,
    sidebar_background_color: null,
    sidebar_text_color: null,
};

function getErrorMessage(error: unknown, fallback: string): string {
    return getApiErrorMessage(error, fallback);
}

function normalizeOptional(value: string | null | undefined): string | null {
    if (value == null) {
        return null;
    }
    const normalized = value.trim();
    return normalized.length > 0 ? normalized : null;
}

function normalizeHexColor(value: string | null | undefined): string | null {
    const normalized = normalizeOptional(value);
    if (!normalized) {
        return null;
    }
    return normalized.toUpperCase();
}

function getColorPickerValue(
    value: string | null | undefined,
    fallback: string,
): string {
    return normalizeHexColor(value) ?? fallback;
}

function normalizePositiveDecimalString(value: string | null | undefined): string | null {
    const normalized = normalizeOptional(value);
    if (!normalized) {
        return null;
    }

    const parsed = Number(normalized);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return null;
    }

    return normalized;
}

function formatRateSource(value: string | null | undefined): string {
    if (!value) {
        return "Not set";
    }

    return value
        .split("_")
        .join(" ")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function formatRateAsOf(value: string | null | undefined): string {
    if (!value) {
        return "Not set";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }

    return parsed.toLocaleString("en-US");
}

function buildFormState(tenant: Tenant): CompanySettingsFormState {
    return {
        name: tenant.name,
        legal_name: tenant.legal_name ?? null,
        address_line_1: tenant.address_line_1 ?? null,
        address_line_2: tenant.address_line_2 ?? null,
        city: tenant.city ?? null,
        state_region: tenant.state_region ?? null,
        postal_code: tenant.postal_code ?? null,
        country: tenant.country ?? null,
        vat_number: tenant.vat_number ?? null,
        default_currency: tenant.default_currency?.toUpperCase() || "USD",
        secondary_currency: tenant.secondary_currency?.toUpperCase() ?? null,
        secondary_currency_rate: tenant.secondary_currency_rate ?? "",
        secondary_currency_rate_source: tenant.secondary_currency_rate_source ?? null,
        secondary_currency_rate_as_of: tenant.secondary_currency_rate_as_of ?? null,
        brand_primary_color: tenant.brand_primary_color?.toUpperCase() ?? null,
        brand_secondary_color: tenant.brand_secondary_color?.toUpperCase() ?? null,
        sidebar_background_color: tenant.sidebar_background_color?.toUpperCase() ?? null,
        sidebar_text_color: tenant.sidebar_text_color?.toUpperCase() ?? null,
    };
}

export default function CompanySettingsForm() {
    const auth = useAuth();
    const toast = useToast();
    const [form, setForm] = useState<CompanySettingsFormState>(DEFAULT_FORM_STATE);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [loadError, setLoadError] = useState<string>("");
    const [saveError, setSaveError] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const previewTheme = useMemo(
        () =>
            resolveTenantTheme({
                brand_primary_color: form.brand_primary_color ?? null,
                brand_secondary_color: form.brand_secondary_color ?? null,
                sidebar_background_color: form.sidebar_background_color ?? null,
                sidebar_text_color: form.sidebar_text_color ?? null,
            }),
        [
            form.brand_primary_color,
            form.brand_secondary_color,
            form.sidebar_background_color,
            form.sidebar_text_color,
        ],
    );

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadTenant(): Promise<void> {
            try {
                setIsLoading(true);
                setLoadError("");
                const tenant = await getCurrentTenant();
                if (!isMounted) {
                    return;
                }
                setForm(buildFormState(tenant));
            } catch (error) {
                if (isMounted) {
                    setLoadError(
                        getErrorMessage(
                            error,
                            "The company settings could not be loaded from the backend.",
                        ),
                    );
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadTenant();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    function updateField<K extends keyof CompanySettingsFormState>(
        field: K,
        value: CompanySettingsFormState[K],
    ): void {
        setForm((current) => ({
            ...current,
            [field]: value,
        }));
    }

    function updateColorField(field: BrandColorField, value: string | null): void {
        updateField(field, (value ? value.toUpperCase() : null) as CompanySettingsFormState[typeof field]);
    }

    function validateForm(): string | null {
        const companyName = form.name.trim();
        const defaultCurrency = form.default_currency.trim().toUpperCase();
        const secondaryCurrency = form.secondary_currency?.trim().toUpperCase() || null;
        const secondaryCurrencyRate = normalizePositiveDecimalString(form.secondary_currency_rate);

        if (!companyName) {
            return "Company name is required.";
        }

        if (!/^[A-Z]{3}$/.test(defaultCurrency)) {
            return "Default currency must be a valid ISO 4217 3-letter code.";
        }

        if (secondaryCurrency && !/^[A-Z]{3}$/.test(secondaryCurrency)) {
            return "Secondary currency must be a valid ISO 4217 3-letter code.";
        }

        if (secondaryCurrency && secondaryCurrency === defaultCurrency) {
            return "Secondary currency must differ from the default currency.";
        }

        if (!secondaryCurrency && form.secondary_currency_rate.trim().length > 0) {
            return "Secondary currency rate requires a configured secondary currency.";
        }

        if (form.secondary_currency_rate.trim().length > 0 && !secondaryCurrencyRate) {
            return "Secondary currency rate must be a positive decimal value.";
        }

        for (const [label, value] of [
            ["Primary color", form.brand_primary_color],
            ["Secondary color", form.brand_secondary_color],
            ["Sidebar background color", form.sidebar_background_color],
            ["Sidebar text color", form.sidebar_text_color],
        ] as const) {
            const normalized = normalizeHexColor(value);
            if (normalized && !/^#[0-9A-F]{6}$/.test(normalized)) {
                return `${label} must use the #RRGGBB hex format.`;
            }
        }

        return null;
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();
        setSaveError("");
        setSuccessMessage("");

        const validationError = validateForm();
        if (validationError) {
            setSaveError(validationError);
            return;
        }

        try {
            setIsSaving(true);
            const updated = await updateCurrentTenant({
                name: form.name.trim(),
                legal_name: normalizeOptional(form.legal_name),
                address_line_1: normalizeOptional(form.address_line_1),
                address_line_2: normalizeOptional(form.address_line_2),
                city: normalizeOptional(form.city),
                state_region: normalizeOptional(form.state_region),
                postal_code: normalizeOptional(form.postal_code),
                country: normalizeOptional(form.country),
                vat_number: normalizeOptional(form.vat_number),
                default_currency: form.default_currency.trim().toUpperCase(),
                secondary_currency: normalizeOptional(form.secondary_currency)?.toUpperCase() ?? null,
                secondary_currency_rate: normalizePositiveDecimalString(form.secondary_currency_rate),
                brand_primary_color: normalizeHexColor(form.brand_primary_color),
                brand_secondary_color: normalizeHexColor(form.brand_secondary_color),
                sidebar_background_color: normalizeHexColor(form.sidebar_background_color),
                sidebar_text_color: normalizeHexColor(form.sidebar_text_color),
            });
            setForm(buildFormState(updated));
            notifyTenantBrandingChanged();
            const message = "Company settings saved.";
            setSuccessMessage(message);
            toast.success(message);
        } catch (error) {
            const message = getErrorMessage(error, "Failed to save company settings.");
            setSaveError(message);
            toast.error(message);
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <div className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                        <h2 className="text-xl font-semibold text-slate-900">Company profile</h2>
                        <p className="mt-1 text-sm text-slate-600">
                            Manage the tenant-facing legal profile and finance defaults used across the current launch-ready product.
                        </p>
                    </div>
                    <Link
                        href="/settings/branding"
                        className="inline-flex rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                    >
                        Manage logo
                    </Link>
                </div>

                {isLoading ? (
                    <p className="mt-6 text-sm text-slate-600">Loading company settings...</p>
                ) : (
                    <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                        <div className="grid gap-4 md:grid-cols-2">
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-name">
                                    Company name
                                </label>
                                <input
                                    id="tenant-name"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={form.name}
                                    onChange={(event) => updateField("name", event.target.value)}
                                    placeholder="Northwind Workspace"
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-legal-name">
                                    Legal name
                                </label>
                                <input
                                    id="tenant-legal-name"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={form.legal_name ?? ""}
                                    onChange={(event) => updateField("legal_name", event.target.value || null)}
                                    placeholder="Northwind Labs AB"
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-vat-number">
                                    VAT / tax identifier
                                </label>
                                <input
                                    id="tenant-vat-number"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={form.vat_number ?? ""}
                                    onChange={(event) => updateField("vat_number", event.target.value || null)}
                                    placeholder="SE123456789001"
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-default-currency">
                                    Default currency
                                </label>
                                <input
                                    id="tenant-default-currency"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                                    value={form.default_currency}
                                    onChange={(event) => updateField("default_currency", event.target.value.toUpperCase())}
                                    placeholder="USD"
                                    maxLength={3}
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-secondary-currency">
                                    Secondary currency
                                </label>
                                <input
                                    id="tenant-secondary-currency"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                                    value={form.secondary_currency ?? ""}
                                    onChange={(event) =>
                                        updateField("secondary_currency", event.target.value.toUpperCase() || null)
                                    }
                                    placeholder="EUR"
                                    maxLength={3}
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-secondary-currency-rate">
                                    Secondary currency rate
                                </label>
                                <input
                                    id="tenant-secondary-currency-rate"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={form.secondary_currency_rate}
                                    onChange={(event) => updateField("secondary_currency_rate", event.target.value)}
                                    placeholder="0.091500"
                                    inputMode="decimal"
                                />
                                <p className="mt-2 text-xs text-slate-500">
                                    Manual operator-managed rate for the configured default ↔ secondary currency pair. No live FX feed is implied.
                                </p>
                            </div>
                            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                                    Current FX metadata
                                </p>
                                <p className="mt-2 text-sm text-slate-700">
                                    Source: {formatRateSource(form.secondary_currency_rate_source)}
                                </p>
                                <p className="mt-1 text-sm text-slate-700">
                                    As of: {formatRateAsOf(form.secondary_currency_rate_as_of)}
                                </p>
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                            <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                                Address
                            </h3>
                            <div className="mt-4 grid gap-4 md:grid-cols-2">
                                <div className="md:col-span-2">
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-address-line-1">
                                        Address line 1
                                    </label>
                                    <input
                                        id="tenant-address-line-1"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.address_line_1 ?? ""}
                                        onChange={(event) => updateField("address_line_1", event.target.value || null)}
                                        placeholder="Sveavagen 1"
                                    />
                                </div>
                                <div className="md:col-span-2">
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-address-line-2">
                                        Address line 2
                                    </label>
                                    <input
                                        id="tenant-address-line-2"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.address_line_2 ?? ""}
                                        onChange={(event) => updateField("address_line_2", event.target.value || null)}
                                        placeholder="Floor 4"
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-city">
                                        City
                                    </label>
                                    <input
                                        id="tenant-city"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.city ?? ""}
                                        onChange={(event) => updateField("city", event.target.value || null)}
                                        placeholder="Stockholm"
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-state-region">
                                        State / region
                                    </label>
                                    <input
                                        id="tenant-state-region"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.state_region ?? ""}
                                        onChange={(event) => updateField("state_region", event.target.value || null)}
                                        placeholder="Stockholm County"
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-postal-code">
                                        Postal code
                                    </label>
                                    <input
                                        id="tenant-postal-code"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.postal_code ?? ""}
                                        onChange={(event) => updateField("postal_code", event.target.value || null)}
                                        placeholder="111 57"
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="tenant-country">
                                        Country
                                    </label>
                                    <input
                                        id="tenant-country"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.country ?? ""}
                                        onChange={(event) => updateField("country", event.target.value || null)}
                                        placeholder="Sweden"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                            <div className="flex flex-wrap items-start justify-between gap-4">
                                <div>
                                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                                        Brand Identity
                                    </h3>
                                    <p className="mt-2 max-w-2xl text-sm text-slate-600">
                                        Set the tenant brand colors used for the sidebar and shared UI highlights. Leave a field blank to keep the product fallback colors.
                                    </p>
                                </div>
                                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                                        Live preview
                                    </p>
                                    <div className="mt-3 overflow-hidden rounded-xl border border-slate-200">
                                        <div
                                            className="px-4 py-4"
                                            style={{
                                                backgroundColor: previewTheme.sidebarBackground,
                                                color: previewTheme.sidebarText,
                                            }}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div
                                                    className="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold"
                                                    style={{
                                                        backgroundColor: previewTheme.brandPrimary,
                                                        color: previewTheme.brandPrimaryContrast,
                                                    }}
                                                >
                                                    SC
                                                </div>
                                                <div>
                                                    <p className="text-sm font-semibold">SupaCRM</p>
                                                    <p
                                                        className="text-xs"
                                                        style={{ color: previewTheme.sidebarMutedText }}
                                                    >
                                                        Tenant preview
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="mt-4 space-y-2">
                                                <div
                                                    className="rounded-lg px-3 py-2 text-sm font-medium"
                                                    style={{
                                                        backgroundColor: previewTheme.sidebarActiveBackground,
                                                        color: previewTheme.sidebarActiveText,
                                                    }}
                                                >
                                                    Active navigation item
                                                </div>
                                                <div
                                                    className="rounded-lg px-3 py-2 text-sm"
                                                    style={{
                                                        backgroundColor: previewTheme.sidebarHoverBackground,
                                                        color: previewTheme.sidebarText,
                                                    }}
                                                >
                                                    Hover state preview
                                                </div>
                                            </div>
                                        </div>
                                        <div className="space-y-3 bg-white px-4 py-4">
                                            <button
                                                type="button"
                                                className="rounded-lg px-4 py-2 text-sm font-medium"
                                                style={{
                                                    backgroundColor: previewTheme.brandPrimary,
                                                    color: previewTheme.brandPrimaryContrast,
                                                }}
                                            >
                                                Primary action
                                            </button>
                                            <p
                                                className="text-sm font-medium"
                                                style={{ color: previewTheme.brandPrimary }}
                                            >
                                                Branded link and highlight preview
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="mt-6 grid gap-4 md:grid-cols-2">
                                {[
                                    {
                                        field: "brand_primary_color",
                                        label: "Primary Color",
                                        placeholder: "#2563EB",
                                    },
                                    {
                                        field: "brand_secondary_color",
                                        label: "Secondary Color",
                                        placeholder: "#1D4ED8",
                                    },
                                    {
                                        field: "sidebar_background_color",
                                        label: "Sidebar Background Color",
                                        placeholder: "#111827",
                                    },
                                    {
                                        field: "sidebar_text_color",
                                        label: "Sidebar Text Color",
                                        placeholder: "#FFFFFF",
                                    },
                                ].map((item) => (
                                    <div key={item.field}>
                                        <label
                                            className="mb-2 block text-sm font-medium text-slate-700"
                                            htmlFor={item.field}
                                        >
                                            {item.label}
                                        </label>
                                        <div className="flex items-center gap-3">
                                            <input
                                                aria-label={`${item.label} picker`}
                                                type="color"
                                                className="h-10 w-10 shrink-0 cursor-pointer rounded-lg border border-slate-300 bg-transparent p-1"
                                                value={getColorPickerValue(
                                                    form[item.field as BrandColorField] as string | null | undefined,
                                                    item.placeholder,
                                                )}
                                                onChange={(event) =>
                                                    updateColorField(
                                                        item.field as BrandColorField,
                                                        event.target.value,
                                                    )
                                                }
                                            />
                                            <input
                                                id={item.field}
                                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                                                value={(form[item.field as BrandColorField] as string | null | undefined) ?? ""}
                                                onChange={(event) =>
                                                    updateColorField(
                                                        item.field as BrandColorField,
                                                        event.target.value || null,
                                                    )
                                                }
                                                placeholder={item.placeholder}
                                                maxLength={7}
                                                spellCheck={false}
                                            />
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    updateColorField(item.field as BrandColorField, null)
                                                }
                                                className="shrink-0 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                            >
                                                Default
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {loadError ? (
                            <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                {loadError}
                            </p>
                        ) : null}
                        {saveError ? (
                            <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                {saveError}
                            </p>
                        ) : null}
                        {successMessage ? (
                            <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                                {successMessage}
                            </p>
                        ) : null}

                        <div className="flex justify-end">
                            <button
                                type="submit"
                                disabled={isSaving || isLoading}
                                className="rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                                style={{
                                    backgroundColor: previewTheme.brandPrimary,
                                    color: previewTheme.brandPrimaryContrast,
                                }}
                            >
                                {isSaving ? "Saving..." : "Save company settings"}
                            </button>
                        </div>
                    </form>
                )}
            </section>
        </div>
    );
}

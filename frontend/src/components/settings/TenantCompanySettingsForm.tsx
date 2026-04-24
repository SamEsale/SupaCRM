"use client";

import { useEffect, useState } from "react";

import {
    buildTenantUpdatePayload,
    getCurrentTenant,
    updateCurrentTenant,
} from "@/services/tenants.service";
import type { Tenant } from "@/types/tenant";

type CompanyFormState = {
    name: string;
    legal_name: string;
    address_line_1: string;
    address_line_2: string;
    city: string;
    state_region: string;
    postal_code: string;
    country: string;
    vat_number: string;
    default_currency: string;
    secondary_currency: string;
    secondary_currency_rate: string;
};

function buildFormState(tenant: Tenant): CompanyFormState {
    return {
        name: tenant.name,
        legal_name: tenant.legal_name ?? "",
        address_line_1: tenant.address_line_1 ?? "",
        address_line_2: tenant.address_line_2 ?? "",
        city: tenant.city ?? "",
        state_region: tenant.state_region ?? "",
        postal_code: tenant.postal_code ?? "",
        country: tenant.country ?? "",
        vat_number: tenant.vat_number ?? "",
        default_currency: tenant.default_currency ?? "USD",
        secondary_currency: tenant.secondary_currency ?? "",
        secondary_currency_rate: tenant.secondary_currency_rate ?? "",
    };
}

export default function TenantCompanySettingsForm() {
    const [tenant, setTenant] = useState<Tenant | null>(null);
    const [form, setForm] = useState<CompanyFormState | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [savedMessage, setSavedMessage] = useState<string>("");

    useEffect(() => {
        let isMounted = true;

        async function loadTenant(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                const nextTenant = await getCurrentTenant();
                if (!isMounted) {
                    return;
                }
                setTenant(nextTenant);
                setForm(buildFormState(nextTenant));
            } catch (error) {
                console.error("Failed to load company settings:", error);
                if (isMounted) {
                    setErrorMessage("Company settings could not be loaded.");
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
    }, []);

    function updateField<K extends keyof CompanyFormState>(
        field: K,
        value: CompanyFormState[K],
    ): void {
        setForm((current) => (current ? { ...current, [field]: value } : current));
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();
        if (!tenant || !form) {
            return;
        }

        try {
            setIsSaving(true);
            setErrorMessage("");
            setSavedMessage("");

            const updatedTenant = await updateCurrentTenant(
                buildTenantUpdatePayload(tenant, {
                    name: form.name.trim(),
                    legal_name: form.legal_name.trim() || null,
                    address_line_1: form.address_line_1.trim() || null,
                    address_line_2: form.address_line_2.trim() || null,
                    city: form.city.trim() || null,
                    state_region: form.state_region.trim() || null,
                    postal_code: form.postal_code.trim() || null,
                    country: form.country.trim() || null,
                    vat_number: form.vat_number.trim() || null,
                    default_currency: form.default_currency.trim().toUpperCase(),
                    secondary_currency: form.secondary_currency.trim().toUpperCase() || null,
                    secondary_currency_rate: form.secondary_currency_rate.trim() || null,
                }),
            );

            setTenant(updatedTenant);
            setForm(buildFormState(updatedTenant));
            setSavedMessage("Company settings saved.");
        } catch (error) {
            console.error("Failed to save company settings:", error);
            setErrorMessage("Company settings could not be saved.");
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm text-sm text-slate-600">
                Loading company settings...
            </section>
        );
    }

    if (errorMessage && !form) {
        return (
            <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm text-sm text-red-700">
                {errorMessage}
            </section>
        );
    }

    if (!form) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm text-sm text-slate-600">
                Company settings are not available for this tenant yet.
            </section>
        );
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Company Profile</h2>
            <p className="mt-2 text-sm text-slate-600">
                These fields write directly to the tenant settings contract already exposed by the backend.
            </p>

            <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label htmlFor="tenant-name" className="mb-2 block text-sm font-medium text-slate-700">
                            Workspace name
                        </label>
                        <input
                            id="tenant-name"
                            value={form.name}
                            onChange={(event) => updateField("name", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            required
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-legal-name" className="mb-2 block text-sm font-medium text-slate-700">
                            Legal name
                        </label>
                        <input
                            id="tenant-legal-name"
                            value={form.legal_name}
                            onChange={(event) => updateField("legal_name", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-address-1" className="mb-2 block text-sm font-medium text-slate-700">
                            Address line 1
                        </label>
                        <input
                            id="tenant-address-1"
                            value={form.address_line_1}
                            onChange={(event) => updateField("address_line_1", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-address-2" className="mb-2 block text-sm font-medium text-slate-700">
                            Address line 2
                        </label>
                        <input
                            id="tenant-address-2"
                            value={form.address_line_2}
                            onChange={(event) => updateField("address_line_2", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-city" className="mb-2 block text-sm font-medium text-slate-700">
                            City
                        </label>
                        <input
                            id="tenant-city"
                            value={form.city}
                            onChange={(event) => updateField("city", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-state-region" className="mb-2 block text-sm font-medium text-slate-700">
                            State or region
                        </label>
                        <input
                            id="tenant-state-region"
                            value={form.state_region}
                            onChange={(event) => updateField("state_region", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-postal-code" className="mb-2 block text-sm font-medium text-slate-700">
                            Postal code
                        </label>
                        <input
                            id="tenant-postal-code"
                            value={form.postal_code}
                            onChange={(event) => updateField("postal_code", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-country" className="mb-2 block text-sm font-medium text-slate-700">
                            Country
                        </label>
                        <input
                            id="tenant-country"
                            value={form.country}
                            onChange={(event) => updateField("country", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-vat-number" className="mb-2 block text-sm font-medium text-slate-700">
                            VAT number
                        </label>
                        <input
                            id="tenant-vat-number"
                            value={form.vat_number}
                            onChange={(event) => updateField("vat_number", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-default-currency" className="mb-2 block text-sm font-medium text-slate-700">
                            Default currency
                        </label>
                        <input
                            id="tenant-default-currency"
                            maxLength={3}
                            value={form.default_currency}
                            onChange={(event) => updateField("default_currency", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                            required
                        />
                    </div>

                    <div>
                        <label htmlFor="tenant-secondary-currency" className="mb-2 block text-sm font-medium text-slate-700">
                            Secondary currency
                        </label>
                        <input
                            id="tenant-secondary-currency"
                            maxLength={3}
                            value={form.secondary_currency}
                            onChange={(event) => updateField("secondary_currency", event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                        />
                    </div>
                </div>

                <div>
                    <label htmlFor="tenant-secondary-rate" className="mb-2 block text-sm font-medium text-slate-700">
                        Manual FX rate
                    </label>
                    <input
                        id="tenant-secondary-rate"
                        type="number"
                        min="0"
                        step="0.000001"
                        value={form.secondary_currency_rate}
                        onChange={(event) => updateField("secondary_currency_rate", event.target.value)}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    />
                    <p className="mt-2 text-xs text-slate-500">
                        Leave blank unless a manual secondary-currency rate should be stored for the tenant.
                    </p>
                </div>

                {errorMessage ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {errorMessage}
                    </div>
                ) : null}

                {savedMessage ? (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                        {savedMessage}
                    </div>
                ) : null}

                <div className="flex items-center gap-3">
                    <button
                        type="submit"
                        disabled={isSaving}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSaving ? "Saving..." : "Save company settings"}
                    </button>
                </div>
            </form>
        </section>
    );
}

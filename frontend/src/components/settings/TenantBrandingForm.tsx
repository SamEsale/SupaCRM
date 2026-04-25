"use client";

import { useEffect, useState } from "react";

import {
    buildTenantUpdatePayload,
    getCurrentTenant,
    updateCurrentTenant,
} from "@/services/tenants.service";
import type { Tenant } from "@/types/tenants";

type BrandingFormState = {
    brand_primary_color: string;
    brand_secondary_color: string;
    sidebar_background_color: string;
    sidebar_text_color: string;
};

function buildFormState(tenant: Tenant): BrandingFormState {
    return {
        brand_primary_color: tenant.brand_primary_color ?? "",
        brand_secondary_color: tenant.brand_secondary_color ?? "",
        sidebar_background_color: tenant.sidebar_background_color ?? "",
        sidebar_text_color: tenant.sidebar_text_color ?? "",
    };
}

function ColorField({
    id,
    label,
    value,
    onChange,
}: {
    id: string;
    label: string;
    value: string;
    onChange: (value: string) => void;
}) {
    return (
        <div>
            <label htmlFor={id} className="mb-2 block text-sm font-medium text-slate-700">
                {label}
            </label>
            <div className="flex items-center gap-3">
                <input
                    id={id}
                    value={value}
                    onChange={(event) => onChange(event.target.value)}
                    placeholder="#RRGGBB"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                />
                <div
                    className="h-10 w-10 rounded-lg border border-slate-200"
                    style={{ backgroundColor: value || "#FFFFFF" }}
                />
            </div>
        </div>
    );
}

export default function TenantBrandingForm() {
    const [tenant, setTenant] = useState<Tenant | null>(null);
    const [form, setForm] = useState<BrandingFormState | null>(null);
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
                console.error("Failed to load branding settings:", error);
                if (isMounted) {
                    setErrorMessage("Branding settings could not be loaded.");
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

    function updateField<K extends keyof BrandingFormState>(
        field: K,
        value: BrandingFormState[K],
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
                    brand_primary_color: form.brand_primary_color.trim() || null,
                    brand_secondary_color: form.brand_secondary_color.trim() || null,
                    sidebar_background_color: form.sidebar_background_color.trim() || null,
                    sidebar_text_color: form.sidebar_text_color.trim() || null,
                }),
            );

            setTenant(updatedTenant);
            setForm(buildFormState(updatedTenant));
            setSavedMessage("Branding settings saved.");
        } catch (error) {
            console.error("Failed to save branding settings:", error);
            setErrorMessage("Branding settings could not be saved.");
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm text-sm text-slate-600">
                Loading branding settings...
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
                Branding settings are not available for this tenant yet.
            </section>
        );
    }

    const logoReference =
        tenant?.logo_file_key?.trim()
            ? tenant.logo_file_key
            : "No logo file key is currently stored.";

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Brand Identity</h2>
            <p className="mt-2 text-sm text-slate-600">
                Update the tenant color fields already supported by the backend. File upload is intentionally not exposed in this phase.
            </p>

            <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-medium text-slate-900">Logo reference</p>
                <p className="mt-2 text-sm text-slate-600">{logoReference}</p>
                <p className="mt-2 text-xs text-slate-500">
                    Storage upload is not part of Phase 1, so this page only displays the current reference.
                </p>
            </div>

            <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                    <ColorField
                        id="brand-primary-color"
                        label="Brand primary color"
                        value={form.brand_primary_color}
                        onChange={(value) => updateField("brand_primary_color", value)}
                    />
                    <ColorField
                        id="brand-secondary-color"
                        label="Brand secondary color"
                        value={form.brand_secondary_color}
                        onChange={(value) => updateField("brand_secondary_color", value)}
                    />
                    <ColorField
                        id="sidebar-background-color"
                        label="Sidebar background color"
                        value={form.sidebar_background_color}
                        onChange={(value) => updateField("sidebar_background_color", value)}
                    />
                    <ColorField
                        id="sidebar-text-color"
                        label="Sidebar text color"
                        value={form.sidebar_text_color}
                        onChange={(value) => updateField("sidebar_text_color", value)}
                    />
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
                        {isSaving ? "Saving..." : "Save branding"}
                    </button>
                </div>
            </form>
        </section>
    );
}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getCurrentTenant } from "@/services/tenants.service";
import type { Tenant } from "@/types/tenant";

function formatLabel(value: string): string {
    return value
        .split("_")
        .join(" ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function DetailCard({
    label,
    value,
}: {
    label: string;
    value: string;
}) {
    return (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                {label}
            </p>
            <p className="mt-2 text-lg font-semibold text-slate-900">{value}</p>
        </div>
    );
}

function ShortcutCard({
    href,
    title,
    description,
}: {
    href: string;
    title: string;
    description: string;
}) {
    return (
        <Link
            href={href}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
        >
            <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            <p className="mt-2 text-sm text-slate-600">{description}</p>
        </Link>
    );
}

export default function SettingsOverview() {
    const [tenant, setTenant] = useState<Tenant | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    useEffect(() => {
        let isMounted = true;

        async function loadTenant(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                const nextTenant = await getCurrentTenant();
                if (isMounted) {
                    setTenant(nextTenant);
                }
            } catch (error) {
                console.error("Failed to load tenant settings overview:", error);
                if (isMounted) {
                    setErrorMessage("Workspace settings could not be loaded.");
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

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
                <p className="mt-2 max-w-3xl text-sm text-slate-600">
                    Manage the current tenant profile, workspace identity, and the branding values already supported by the backend.
                </p>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm text-sm text-slate-600">
                    Loading workspace settings...
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm text-sm text-red-700">
                    {errorMessage}
                </section>
            ) : tenant ? (
                <>
                    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <DetailCard label="Workspace" value={tenant.name} />
                        <DetailCard label="Status" value={formatLabel(tenant.status)} />
                        <DetailCard label="Default Currency" value={tenant.default_currency} />
                        <DetailCard
                            label="Logo Reference"
                            value={tenant.logo_file_key?.trim() ? "Configured" : "Not configured"}
                        />
                    </section>

                    <section className="grid gap-4 md:grid-cols-2">
                        <ShortcutCard
                            href="/settings/company"
                            title="Company Settings"
                            description="Edit the legal workspace profile, address details, VAT data, and base currency settings."
                        />
                        <ShortcutCard
                            href="/settings/branding"
                            title="Branding"
                            description="Review the current logo reference and adjust the tenant brand and sidebar color values."
                        />
                    </section>
                </>
            ) : null}
        </main>
    );
}

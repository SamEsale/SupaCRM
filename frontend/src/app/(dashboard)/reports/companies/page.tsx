"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api-errors";
import { getCompanyReportsSnapshot } from "@/services/reporting.service";
import type { CompanyReportsSnapshot } from "@/types/reporting";

function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

export default function CompanyReportsPage() {
    const [snapshot, setSnapshot] = useState<CompanyReportsSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");
            setSnapshot(await getCompanyReportsSnapshot());
        } catch (error) {
            console.error("Failed to load company reports:", error);
            setErrorMessage(
                getApiErrorMessage(error, "The company reports view could not be loaded from the backend."),
            );
            setSnapshot(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadSnapshot();
    }, [loadSnapshot]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Company Reports</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Review company coverage across contacts, sales, invoicing, and support relationships.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/companies"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Open Companies
                        </Link>
                        <Link
                            href="/companies/create"
                            className="rounded-lg bg-[var(--brand-primary)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
                        >
                            Add Company
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading company reports</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching company coverage, relationship counts, and recent company activity from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load company reports</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                    <button
                        type="button"
                        onClick={() => {
                            void loadSnapshot();
                        }}
                        className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Retry
                    </button>
                </section>
            ) : snapshot ? (
                <>
                    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total companies</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.total_companies}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.companies_created_this_period_count} added in the current period.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Companies with contacts</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.companies_with_contacts_count}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.companies_without_contacts_count} companies still have no linked contacts.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Companies with open deals</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.companies_with_open_deals_count}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.companies_with_won_deals_count} companies already have won business.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Invoicing and support coverage</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.companies_with_invoices_count}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.companies_with_support_tickets_count} companies also appear in support.
                            </p>
                        </article>
                    </section>

                    {snapshot.summary.total_companies === 0 ? (
                        <section className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-600 shadow-sm">
                            No companies have been created for this tenant yet. Once companies exist, this report will summarize their linked contacts and business activity.
                        </section>
                    ) : (
                        <section className="grid gap-6 xl:grid-cols-[1.05fr_1.45fr]">
                            <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                <h2 className="text-xl font-semibold text-slate-900">Companies by contact coverage</h2>
                                <p className="mt-2 text-sm text-slate-600">
                                    See which companies have the strongest contact coverage and which still need relationship building.
                                </p>

                                <div className="mt-6 space-y-3">
                                    {snapshot.contact_breakdown.length > 0 ? (
                                        snapshot.contact_breakdown.map((item) => (
                                            <div key={item.company_id} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                                <p className="font-medium text-slate-900">{item.company_name}</p>
                                                <p className="text-sm font-semibold text-slate-900">{item.contact_count}</p>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-600">
                                            No company contact coverage is available yet.
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                <h2 className="text-xl font-semibold text-slate-900">Most recently updated companies</h2>
                                <p className="mt-2 text-sm text-slate-600">
                                    Recent company records with linked CRM, finance, and support activity counts.
                                </p>

                                <div className="mt-6 space-y-3">
                                    {snapshot.recent_companies.length > 0 ? (
                                        snapshot.recent_companies.map((company) => (
                                            <div key={company.company_id} className="rounded-lg border border-slate-200 px-4 py-4">
                                                <div className="flex flex-wrap items-start justify-between gap-3">
                                                    <p className="font-medium text-slate-900">{company.company_name}</p>
                                                    <p className="text-xs text-slate-500">{formatDateTime(company.updated_at)}</p>
                                                </div>
                                                <div className="mt-3 grid gap-2 text-xs text-slate-700 md:grid-cols-2 xl:grid-cols-4">
                                                    <span className="rounded-full bg-slate-100 px-3 py-1">Contacts: {company.contact_count}</span>
                                                    <span className="rounded-full bg-blue-100 px-3 py-1 text-blue-800">Open deals: {company.open_deals_count}</span>
                                                    <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800">Won deals: {company.won_deals_count}</span>
                                                    <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-800">Invoices: {company.invoice_count}</span>
                                                </div>
                                                <p className="mt-3 text-sm text-slate-600">
                                                    Support tickets linked: {company.support_ticket_count}
                                                </p>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-600">
                                            No recent company records are available yet.
                                        </div>
                                    )}
                                </div>
                            </div>
                        </section>
                    )}
                </>
            ) : null}
        </main>
    );
}

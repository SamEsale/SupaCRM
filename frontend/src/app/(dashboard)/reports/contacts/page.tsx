"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api-errors";
import { getContactReportsSnapshot } from "@/services/reporting.service";
import type { ContactReportsSnapshot } from "@/types/reporting";

function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

export default function ContactReportsPage() {
    const [snapshot, setSnapshot] = useState<ContactReportsSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");
            setSnapshot(await getContactReportsSnapshot());
        } catch (error) {
            console.error("Failed to load contact reports:", error);
            setErrorMessage(
                getApiErrorMessage(error, "The contact reports view could not be loaded from the backend."),
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
                        <h1 className="text-3xl font-bold text-slate-900">Contact Reports</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Monitor contact growth, company coverage, sales linkage, and the contacts that need operator attention.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/contacts"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Open Contacts
                        </Link>
                        <Link
                            href="/sales/leads/create"
                            className="rounded-lg bg-[var(--brand-primary)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
                        >
                            Add Lead
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading contact reports</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching contact counts, company breakdowns, and recent contact activity from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load contact reports</h2>
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
                    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total contacts</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.total_contacts}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.contacts_created_this_period_count} created in the current reporting period.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Contacts with open deals</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.contacts_with_open_deals_count}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.contacts_with_won_deals_count} contacts are already linked to won business.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Contacts without company</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.contacts_without_company_count}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.contacts_with_support_tickets_count} contacts currently have support ticket history.
                            </p>
                        </article>
                    </section>

                    {snapshot.summary.total_contacts === 0 ? (
                        <section className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-600 shadow-sm">
                            No contacts have been added for this tenant yet. Once contacts are created, this report will summarize ownership and deal linkage.
                        </section>
                    ) : (
                        <section className="grid gap-6 xl:grid-cols-[1.1fr_1.4fr]">
                            <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                <h2 className="text-xl font-semibold text-slate-900">Contacts by company</h2>
                                <p className="mt-2 text-sm text-slate-600">
                                    Where your contact book currently sits across known companies.
                                </p>

                                <div className="mt-6 space-y-3">
                                    {snapshot.contacts_by_company.length > 0 ? (
                                        snapshot.contacts_by_company.map((item) => (
                                            <div key={item.company_id ?? item.company_name} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                                <div>
                                                    <p className="font-medium text-slate-900">{item.company_name}</p>
                                                    <p className="text-sm text-slate-600">
                                                        {item.company_id ? "Known company relationship" : "No company linked"}
                                                    </p>
                                                </div>
                                                <p className="text-sm font-semibold text-slate-900">{item.contact_count}</p>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-600">
                                            No company-linked contact data is available yet.
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                <h2 className="text-xl font-semibold text-slate-900">Most recently updated contacts</h2>
                                <p className="mt-2 text-sm text-slate-600">
                                    Recent contact activity with deal and support linkage for fast operator follow-up.
                                </p>

                                <div className="mt-6 space-y-3">
                                    {snapshot.recent_contacts.length > 0 ? (
                                        snapshot.recent_contacts.map((contact) => (
                                            <div key={contact.contact_id} className="rounded-lg border border-slate-200 px-4 py-4">
                                                <div className="flex flex-wrap items-start justify-between gap-3">
                                                    <div>
                                                        <p className="font-medium text-slate-900">{contact.full_name}</p>
                                                        <p className="text-sm text-slate-600">{contact.company_name ?? "No company linked"}</p>
                                                    </div>
                                                    <p className="text-xs text-slate-500">{formatDateTime(contact.updated_at)}</p>
                                                </div>
                                                <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-700">
                                                    <span className="rounded-full bg-slate-100 px-3 py-1">Open deals: {contact.open_deals_count}</span>
                                                    <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800">Won deals: {contact.won_deals_count}</span>
                                                    <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-800">Support tickets: {contact.support_ticket_count}</span>
                                                </div>
                                                {contact.email || contact.phone ? (
                                                    <p className="mt-3 text-sm text-slate-600">
                                                        {[contact.email, contact.phone].filter(Boolean).join(" · ")}
                                                    </p>
                                                ) : null}
                                            </div>
                                        ))
                                    ) : (
                                        <div className="rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-600">
                                            No recent contacts are available yet.
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

"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api-errors";
import { getSupportReportsSnapshot } from "@/services/reporting.service";
import type { SupportReportsSnapshot } from "@/types/reporting";

function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

function formatLabel(value: string): string {
    return value
        .split("_")
        .join(" ")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

export default function SupportReportsPage() {
    const [snapshot, setSnapshot] = useState<SupportReportsSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");
            setSnapshot(await getSupportReportsSnapshot());
        } catch (error) {
            console.error("Failed to load support reports:", error);
            setErrorMessage(
                getApiErrorMessage(error, "The support reports view could not be loaded from the backend."),
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
                        <h1 className="text-3xl font-bold text-slate-900">Support Reports</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Track ticket workload, active urgency, and where support is clustering across channels and linked business records.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/support"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Open Support
                        </Link>
                        <Link
                            href="/support/create"
                            className="rounded-lg bg-[var(--brand-primary)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
                        >
                            Create Ticket
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading support reports</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching ticket status, source, and company linkage metrics from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load support reports</h2>
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
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total tickets</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.total_tickets}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.urgent_active_tickets} urgent tickets remain active.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Open and in progress</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {snapshot.summary.open_tickets + snapshot.summary.in_progress_tickets}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.open_tickets} open, {snapshot.summary.in_progress_tickets} in progress.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Waiting on customer</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.waiting_on_customer_tickets}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.resolved_tickets} resolved and {snapshot.summary.closed_tickets} closed overall.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Business linkage</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.summary.tickets_linked_to_deals_count}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.summary.tickets_linked_to_invoices_count} tickets are also linked to invoices.
                            </p>
                        </article>
                    </section>

                    {snapshot.summary.total_tickets === 0 ? (
                        <section className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-600 shadow-sm">
                            No support tickets have been created for this tenant yet. Once support activity starts, this report will summarize queue pressure and ticket sources.
                        </section>
                    ) : (
                        <>
                            <section className="grid gap-6 xl:grid-cols-3">
                                <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                    <h2 className="text-xl font-semibold text-slate-900">Tickets by priority</h2>
                                    <div className="mt-6 space-y-3">
                                        {snapshot.tickets_by_priority.map((item) => (
                                            <div key={item.label} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                                <p className="font-medium text-slate-900">{formatLabel(item.label)}</p>
                                                <p className="text-sm font-semibold text-slate-900">{item.count}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                    <h2 className="text-xl font-semibold text-slate-900">Tickets by source</h2>
                                    <div className="mt-6 space-y-3">
                                        {snapshot.tickets_by_source.map((item) => (
                                            <div key={item.label} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                                <p className="font-medium text-slate-900">{formatLabel(item.label)}</p>
                                                <p className="text-sm font-semibold text-slate-900">{item.count}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                    <h2 className="text-xl font-semibold text-slate-900">Tickets by company</h2>
                                    <div className="mt-6 space-y-3">
                                        {snapshot.tickets_by_company.map((item) => (
                                            <div key={item.company_id ?? item.company_name} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                                <p className="font-medium text-slate-900">{item.company_name}</p>
                                                <p className="text-sm font-semibold text-slate-900">{item.ticket_count}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </section>

                            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                <h2 className="text-xl font-semibold text-slate-900">Recently updated tickets</h2>
                                <p className="mt-2 text-sm text-slate-600">
                                    Recent support records with their source, urgency, and related deal or invoice linkage.
                                </p>

                                <div className="mt-6 space-y-3">
                                    {snapshot.recent_tickets.length > 0 ? (
                                        snapshot.recent_tickets.map((ticket) => (
                                            <div key={ticket.ticket_id} className="rounded-lg border border-slate-200 px-4 py-4">
                                                <div className="flex flex-wrap items-start justify-between gap-3">
                                                    <div>
                                                        <p className="font-medium text-slate-900">{ticket.title}</p>
                                                        <p className="text-sm text-slate-600">
                                                            {ticket.company_name ?? "No company linked"} · {formatLabel(ticket.source)}
                                                        </p>
                                                    </div>
                                                    <p className="text-xs text-slate-500">{formatDateTime(ticket.updated_at)}</p>
                                                </div>
                                                <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-700">
                                                    <span className="rounded-full bg-slate-100 px-3 py-1">{formatLabel(ticket.status)}</span>
                                                    <span className="rounded-full bg-red-100 px-3 py-1 text-red-800">{formatLabel(ticket.priority)}</span>
                                                    {ticket.related_deal_id ? (
                                                        <span className="rounded-full bg-blue-100 px-3 py-1 text-blue-800">Deal linked</span>
                                                    ) : null}
                                                    {ticket.related_invoice_id ? (
                                                        <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-800">Invoice linked</span>
                                                    ) : null}
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-600">
                                            No recently updated tickets are available yet.
                                        </div>
                                    )}
                                </div>
                            </section>
                        </>
                    )}
                </>
            ) : null}
        </main>
    );
}

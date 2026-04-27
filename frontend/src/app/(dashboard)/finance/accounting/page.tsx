"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getAccountingAccounts, getJournalEntries } from "@/services/accounting.service";
import type { AccountingAccount, JournalEntry } from "@/types/accounting";

type AccountingSnapshot = {
    accounts: AccountingAccount[];
    journalEntries: JournalEntry[];
};

function formatMoney(amount: string, currency?: string): string {
    const value = Number(amount);
    if (Number.isNaN(value)) {
        return currency ? `${amount} ${currency}` : amount;
    }
    if (!currency) {
        return new Intl.NumberFormat("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(value);
}

function formatDate(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleDateString("en-US");
}

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

function parseApiError(error: unknown, fallback: string): string {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
            return response.data.detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return fallback;
}

async function loadAccountingSnapshot(sourceType?: string, sourceId?: string): Promise<AccountingSnapshot> {
    const [accountsResponse, journalEntriesResponse] = await Promise.all([
        getAccountingAccounts(),
        getJournalEntries({
            source_type: sourceType || undefined,
            source_id: sourceId || undefined,
            limit: 100,
            offset: 0,
        }),
    ]);

    return {
        accounts: accountsResponse.items ?? [],
        journalEntries: journalEntriesResponse.items ?? [],
    };
}

export default function FinanceAccountingPage() {
    const searchParams = useSearchParams();
    const [snapshot, setSnapshot] = useState<AccountingSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    const sourceType = searchParams.get("source_type") ?? "";
    const sourceId = searchParams.get("source_id") ?? "";

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");
            const nextSnapshot = await loadAccountingSnapshot(sourceType, sourceId);
            setSnapshot(nextSnapshot);
        } catch (error) {
            console.error("Failed to load accounting workspace:", error);
            setErrorMessage(
                parseApiError(error, "The accounting workspace could not be loaded from the backend."),
            );
            setSnapshot(null);
        } finally {
            setIsLoading(false);
        }
    }, [sourceId, sourceType]);

    useEffect(() => {
        void loadSnapshot();
    }, [loadSnapshot]);

    const journalCurrencies = useMemo(() => {
        const currencies = new Set((snapshot?.journalEntries ?? []).map((entry) => entry.currency));
        return Array.from(currencies).sort();
    }, [snapshot]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Accounting</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Review the tenant chart of accounts and invoice-linked journal activity without jumping into a broader ERP workflow.
                        </p>
                        {sourceType || sourceId ? (
                            <p className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                                Filtered to <span className="font-medium">{sourceType || "all sources"}</span>
                                {sourceId ? ` / ${sourceId}` : ""}.
                            </p>
                        ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/reports/finance"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Open Finance Reports
                        </Link>
                        <Link
                            href="/finance"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Back to Finance
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading accounting workspace</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching chart of accounts and journal entries from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load accounting</h2>
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
                    {journalCurrencies.length > 1 ? (
                        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                            <p className="text-sm text-amber-900">
                                Journal entries currently span multiple currencies ({journalCurrencies.join(", ")}). Totals are shown per entry without FX normalization.
                            </p>
                        </section>
                    ) : null}

                    <section className="grid gap-4 md:grid-cols-3">
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Accounts</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.accounts.length}</p>
                            <p className="mt-2 text-sm text-slate-600">Default system accounts are provisioned automatically per tenant.</p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Journal entries</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{snapshot.journalEntries.length}</p>
                            <p className="mt-2 text-sm text-slate-600">Invoice-issued and invoice-paid events post here in the current launch slice.</p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Filtered source</p>
                            <p className="mt-3 text-xl font-bold text-slate-900">
                                {sourceType ? formatLabel(sourceType) : "All accounting activity"}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                {sourceId ? `Source id: ${sourceId}` : "No source filter applied."}
                            </p>
                        </article>
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Chart of Accounts</h2>
                        <p className="mt-2 text-sm text-slate-600">
                            Launch-scope accounts available for invoice-driven postings and financial statements.
                        </p>
                        <div className="mt-6 overflow-x-auto">
                            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                                <thead className="bg-slate-50 text-slate-600">
                                    <tr>
                                        <th className="px-4 py-3 font-medium">Code</th>
                                        <th className="px-4 py-3 font-medium">Name</th>
                                        <th className="px-4 py-3 font-medium">Type</th>
                                        <th className="px-4 py-3 font-medium">System</th>
                                        <th className="px-4 py-3 font-medium">Status</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-200 bg-white">
                                    {snapshot.accounts.map((account) => (
                                        <tr key={account.id}>
                                            <td className="px-4 py-3 font-medium text-slate-900">{account.code}</td>
                                            <td className="px-4 py-3 text-slate-700">{account.name}</td>
                                            <td className="px-4 py-3 text-slate-700">{formatLabel(account.account_type)}</td>
                                            <td className="px-4 py-3 text-slate-700">
                                                {account.system_key ? formatLabel(account.system_key) : "Manual"}
                                            </td>
                                            <td className="px-4 py-3 text-slate-700">{account.is_active ? "Active" : "Inactive"}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Journal Entries</h2>
                        <p className="mt-2 text-sm text-slate-600">
                            Balanced entries posted from supported invoice events.
                        </p>

                        <div className="mt-6 space-y-4">
                            {snapshot.journalEntries.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                    No journal entries match the current tenant and filters yet.
                                </div>
                            ) : (
                                snapshot.journalEntries.map((entry) => (
                                    <article key={entry.id} className="rounded-xl border border-slate-200 p-5">
                                        <div className="flex flex-wrap items-start justify-between gap-4">
                                            <div>
                                                <h3 className="text-lg font-semibold text-slate-900">{entry.memo}</h3>
                                                <p className="mt-1 text-sm text-slate-600">
                                                    {formatDate(entry.entry_date)} · {entry.source_type ? formatLabel(entry.source_type) : "Manual"}
                                                    {entry.source_event ? ` / ${formatLabel(entry.source_event)}` : ""}
                                                </p>
                                            </div>
                                            <div className="text-right text-sm text-slate-700">
                                                <p className="font-medium text-slate-900">
                                                    {formatMoney(entry.total_debit, entry.currency)}
                                                </p>
                                                <p>Debit = Credit</p>
                                                <p className="mt-1 text-xs text-slate-500">{formatDateTime(entry.created_at)}</p>
                                            </div>
                                        </div>

                                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                                            {entry.lines.map((line) => (
                                                <div key={line.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                                                    <p className="text-sm font-medium text-slate-900">
                                                        {line.account_code} · {line.account_name}
                                                    </p>
                                                    <p className="mt-1 text-sm text-slate-600">
                                                        {line.debit_amount !== "0.00"
                                                            ? `Debit ${formatMoney(line.debit_amount, entry.currency)}`
                                                            : `Credit ${formatMoney(line.credit_amount, entry.currency)}`}
                                                    </p>
                                                    {line.description ? (
                                                        <p className="mt-1 text-xs text-slate-500">{line.description}</p>
                                                    ) : null}
                                                </div>
                                            ))}
                                        </div>
                                    </article>
                                ))
                            )}
                        </div>
                    </section>
                </>
            ) : null}
        </main>
    );
}

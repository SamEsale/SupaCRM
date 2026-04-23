"use client";

import Link from "next/link";
import { type ReactElement, useCallback, useEffect, useState } from "react";

import type { FinancialStatementLine } from "@/types/accounting";
import { getFinanceReportsSnapshot, type FinanceReportsSnapshot } from "@/services/reporting.service";

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

function formatStatus(value: string): string {
    return value
        .split("_")
        .join(" ")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function renderStatementLines(lines: FinancialStatementLine[]): ReactElement {
    if (lines.length === 0) {
        return (
            <div className="rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-600">
                No posted balances yet.
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {lines.map((line) => (
                <div key={`${line.account_id}-${line.code}`} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                    <div>
                        <p className="font-medium text-slate-900">{line.code} · {line.name}</p>
                        <p className="text-sm text-slate-600">
                            {line.currencies.length === 1 ? line.currencies[0] : "Mixed currencies"}
                        </p>
                    </div>
                    <p className="text-sm font-medium text-slate-900">
                        {line.currencies.length === 1
                            ? formatMoney(line.total_amount, line.currencies[0])
                            : "Mixed currencies"}
                    </p>
                </div>
            ))}
        </div>
    );
}

export default function FinanceReportsPage() {
    const [snapshot, setSnapshot] = useState<FinanceReportsSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");
            const nextSnapshot = await getFinanceReportsSnapshot();
            setSnapshot(nextSnapshot);
        } catch (error) {
            console.error("Failed to load finance reports:", error);
            setErrorMessage(
                parseApiError(error, "The finance reports view could not be loaded from the backend."),
            );
            setSnapshot(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadSnapshot();
    }, [loadSnapshot]);

    const reportCurrencies = snapshot?.financial_statements.profit_and_loss.currencies ?? [];
    const displayCurrency = reportCurrencies.length === 1 ? reportCurrencies[0] : undefined;

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Finance Reports</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Connect invoicing activity to launch-scope accounting statements and receivables visibility.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/finance/accounting"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Open Accounting
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
                    <h2 className="text-xl font-semibold text-slate-900">Loading finance reports</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching revenue flow, financial statements, and receivables from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load finance reports</h2>
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
                    {(snapshot.revenue_flow.summary.invoice_currencies.length > 1
                        || snapshot.financial_statements.profit_and_loss.currencies.length > 1
                        || snapshot.financial_statements.receivables.currencies.length > 1
                        || snapshot.payments_summary.payment_currencies.length > 1) ? (
                        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                            <p className="text-sm text-amber-900">
                                Finance reporting currently spans multiple currencies and is shown without FX normalization.
                            </p>
                        </section>
                    ) : null}

                    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recognized revenue</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {formatMoney(snapshot.financial_statements.profit_and_loss.total_revenue, displayCurrency)}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">Posted from issued invoices in the current launch slice.</p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recorded payments</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {snapshot.payments_summary.payment_currencies.length === 1
                                    ? formatMoney(
                                        snapshot.payments_summary.completed_payment_amount,
                                        snapshot.payments_summary.payment_currencies[0],
                                    )
                                    : snapshot.payments_summary.payment_currencies.length > 1
                                        ? "Mixed currencies"
                                        : "0"}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.payments_summary.completed_payment_count} completed payment records.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Open receivables</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {snapshot.financial_statements.receivables.currencies.length === 1
                                    ? formatMoney(
                                        snapshot.financial_statements.receivables.open_receivables_amount,
                                        snapshot.financial_statements.receivables.currencies[0],
                                    )
                                    : "Mixed currencies"}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.financial_statements.receivables.issued_invoice_count} issued, {snapshot.financial_statements.receivables.overdue_invoice_count} overdue.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Paid invoices</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {snapshot.revenue_flow.summary.invoice_paid_count}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.payments_summary.pending_payment_count} pending payment records still need attention.
                            </p>
                        </article>
                    </section>

                    <section className="grid gap-6 xl:grid-cols-2">
                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Profit &amp; Loss</h2>
                            <p className="mt-2 text-sm text-slate-600">
                                Revenue and expense balances recognized from posted accounting events.
                            </p>

                            <div className="mt-6 space-y-5">
                                <div>
                                    <div className="mb-3 flex items-center justify-between gap-4">
                                        <h3 className="font-medium text-slate-900">Revenue</h3>
                                        <p className="text-sm font-medium text-slate-900">
                                            {formatMoney(snapshot.financial_statements.profit_and_loss.total_revenue, displayCurrency)}
                                        </p>
                                    </div>
                                    {renderStatementLines(snapshot.financial_statements.profit_and_loss.revenue_lines)}
                                </div>

                                <div>
                                    <div className="mb-3 flex items-center justify-between gap-4">
                                        <h3 className="font-medium text-slate-900">Expenses</h3>
                                        <p className="text-sm font-medium text-slate-900">
                                            {formatMoney(snapshot.financial_statements.profit_and_loss.total_expenses, displayCurrency)}
                                        </p>
                                    </div>
                                    {renderStatementLines(snapshot.financial_statements.profit_and_loss.expense_lines)}
                                </div>
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Balance Sheet</h2>
                            <p className="mt-2 text-sm text-slate-600">
                                Launch-scope asset, liability, and equity balances from the posted accounting layer.
                            </p>

                            <div className="mt-6 space-y-5">
                                <div>
                                    <div className="mb-3 flex items-center justify-between gap-4">
                                        <h3 className="font-medium text-slate-900">Assets</h3>
                                        <p className="text-sm font-medium text-slate-900">
                                            {formatMoney(snapshot.financial_statements.balance_sheet.total_assets, displayCurrency)}
                                        </p>
                                    </div>
                                    {renderStatementLines(snapshot.financial_statements.balance_sheet.asset_lines)}
                                </div>

                                <div>
                                    <div className="mb-3 flex items-center justify-between gap-4">
                                        <h3 className="font-medium text-slate-900">Liabilities</h3>
                                        <p className="text-sm font-medium text-slate-900">
                                            {formatMoney(snapshot.financial_statements.balance_sheet.total_liabilities, displayCurrency)}
                                        </p>
                                    </div>
                                    {renderStatementLines(snapshot.financial_statements.balance_sheet.liability_lines)}
                                </div>

                                <div>
                                    <div className="mb-3 flex items-center justify-between gap-4">
                                        <h3 className="font-medium text-slate-900">Equity</h3>
                                        <p className="text-sm font-medium text-slate-900">
                                            {formatMoney(snapshot.financial_statements.balance_sheet.total_equity, displayCurrency)}
                                        </p>
                                    </div>
                                    {renderStatementLines(snapshot.financial_statements.balance_sheet.equity_lines)}
                                </div>
                            </div>
                        </div>
                    </section>

                    <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-xl font-semibold text-slate-900">Receivables</h2>
                                    <p className="mt-2 text-sm text-slate-600">
                                        Open invoice balances remain the truthful receivables signal in this phase.
                                    </p>
                                </div>
                                <Link href="/finance/invoices" className="text-sm font-medium text-slate-700 underline underline-offset-2">
                                    View invoices
                                </Link>
                            </div>

                            <div className="mt-6 space-y-3">
                                {snapshot.financial_statements.receivables.items.map((invoice) => (
                                    <div key={invoice.invoice_id} className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                        <div>
                                            <Link
                                                href={`/finance/invoices/${invoice.invoice_id}`}
                                                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
                                            >
                                                {invoice.invoice_number}
                                            </Link>
                                            <p className="text-sm text-slate-600">
                                                {formatStatus(invoice.status)} · due {invoice.due_date}
                                            </p>
                                            <p className="mt-1 text-xs text-slate-500">
                                                Paid {formatMoney(invoice.paid_amount, invoice.currency)} · outstanding {formatMoney(invoice.outstanding_amount, invoice.currency)}
                                            </p>
                                        </div>
                                        <p className="text-sm font-medium text-slate-900">
                                            {formatMoney(invoice.total_amount, invoice.currency)}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Lifecycle consistency</h2>
                            <p className="mt-2 text-sm text-slate-600">
                                This keeps Sales and Finance reading from the same commercial story.
                            </p>

                            <div className="mt-6 space-y-3">
                                <div className="rounded-lg border border-slate-200 px-4 py-3">
                                    <p className="text-sm font-medium text-slate-900">Open pipeline</p>
                                    <p className="mt-1 text-sm text-slate-600">
                                        {snapshot.revenue_flow.sales_summary.currencies.length === 1
                                            ? formatMoney(
                                                snapshot.revenue_flow.sales_summary.total_open_pipeline_amount,
                                                snapshot.revenue_flow.sales_summary.currencies[0],
                                            )
                                            : "Mixed currencies"}
                                    </p>
                                </div>
                                <div className="rounded-lg border border-slate-200 px-4 py-3">
                                    <p className="text-sm font-medium text-slate-900">Quotes created this period</p>
                                    <p className="mt-1 text-sm text-slate-600">
                                        {snapshot.revenue_flow.summary.quote_created_this_period_count}
                                    </p>
                                </div>
                                <div className="rounded-lg border border-slate-200 px-4 py-3">
                                    <p className="text-sm font-medium text-slate-900">Invoices created this period</p>
                                    <p className="mt-1 text-sm text-slate-600">
                                        {snapshot.revenue_flow.summary.invoice_created_this_period_count}
                                    </p>
                                </div>
                                <div className="rounded-lg border border-slate-200 px-4 py-3">
                                    <p className="text-sm font-medium text-slate-900">Completed payments</p>
                                    <p className="mt-1 text-sm text-slate-600">
                                        {snapshot.payments_summary.completed_payment_count}
                                    </p>
                                </div>
                                <div className="rounded-lg border border-slate-200 px-4 py-3">
                                    <p className="text-sm font-medium text-slate-900">Payment status breakdown</p>
                                    <div className="mt-2 space-y-2">
                                        {snapshot.payment_status_breakdown.length === 0 ? (
                                            <p className="text-sm text-slate-600">No payment records yet.</p>
                                        ) : (
                                            snapshot.payment_status_breakdown.map((item) => (
                                                <div key={item.status} className="flex items-center justify-between gap-3 text-sm text-slate-600">
                                                    <span>{formatStatus(item.status)}</span>
                                                    <span>
                                                        {item.count} · {item.currencies.length === 1
                                                            ? formatMoney(item.total_amount, item.currencies[0])
                                                            : "Mixed currencies"}
                                                    </span>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                                    <p className="text-sm font-medium text-amber-900">VAT reporting</p>
                                    <p className="mt-1 text-sm text-amber-800">{snapshot.financial_statements.vat_note}</p>
                                </div>
                            </div>
                        </div>
                    </section>
                </>
            ) : null}
        </main>
    );
}

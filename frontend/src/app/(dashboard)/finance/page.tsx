"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import {
    getMissingSecondaryCurrencyRateMessage,
    getSecondaryCurrencyDisplay,
} from "@/lib/finance-currency";
import { getExpenses } from "@/services/expenses.service";
import { getInvoices } from "@/services/invoices.service";
import { getQuotes } from "@/services/quotes.service";
import { getRevenueFlowReport } from "@/services/reporting.service";
import { getCurrentTenant } from "@/services/tenants.service";
import type { Expense } from "@/types/expenses";
import type { Invoice, Quote, RevenueFlowReport, RevenueStatusBreakdown } from "@/types/finance";
import type { Tenant } from "@/types/tenants";

function formatMoney(amount: string, currency: string): string {
    const value = Number(amount);

    if (Number.isNaN(value)) {
        return `${amount} ${currency}`;
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(value);
}

function formatStatus(value: string): string {
    return value
        .split("_")
        .join(" ")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function formatBreakdownAmount(item: RevenueStatusBreakdown): string {
    if (item.currencies.length !== 1) {
        return "Mixed currencies";
    }
    return formatMoney(item.total_amount, item.currencies[0]);
}

export default function FinancePage() {
    const auth = useAuth();
    const [tenant, setTenant] = useState<Tenant | null>(null);
    const [report, setReport] = useState<RevenueFlowReport | null>(null);
    const [recentQuotes, setRecentQuotes] = useState<Quote[]>([]);
    const [recentInvoices, setRecentInvoices] = useState<Invoice[]>([]);
    const [recentExpenses, setRecentExpenses] = useState<Expense[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setTenant(null);
            setReport(null);
            setRecentQuotes([]);
            setRecentInvoices([]);
            setRecentExpenses([]);
            setErrorMessage("");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function load(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const [tenantResponse, reportResponse, quotesResponse, invoicesResponse, expensesResponse] = await Promise.all([
                    getCurrentTenant(),
                    getRevenueFlowReport(),
                    getQuotes({ limit: 5, offset: 0 }),
                    getInvoices({ limit: 5, offset: 0 }),
                    getExpenses({ limit: 5, offset: 0 }),
                ]);

                if (!isMounted) {
                    return;
                }

                setTenant(tenantResponse);
                setReport(reportResponse);
                setRecentQuotes(quotesResponse.items ?? []);
                setRecentInvoices(invoicesResponse.items ?? []);
                setRecentExpenses(expensesResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load finance overview:", error);

                if (!isMounted) {
                    return;
                }

                setErrorMessage("The finance overview could not be loaded from the backend.");
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void load();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    const salesCurrencyLabel = useMemo(() => {
        if (!report) {
            return "";
        }
        return report.sales_summary.currencies.length === 1
            ? report.sales_summary.currencies[0]
            : "Mixed currencies";
    }, [report]);

    const expenseCurrencies = useMemo(() => {
        return Array.from(new Set(recentExpenses.map((expense) => expense.currency))).sort();
    }, [recentExpenses]);

    const expenseActionCount = useMemo(() => {
        return recentExpenses.filter((expense) => expense.status === "submitted" || expense.status === "approved").length;
    }, [recentExpenses]);

    const secondaryCurrencyNotice = useMemo(() => {
        if (!tenant?.secondary_currency) {
            return null;
        }

        if (tenant.secondary_currency_rate && tenant.secondary_currency_rate_as_of) {
            return `Secondary currency view uses a saved manual rate for ${tenant.default_currency} ↔ ${tenant.secondary_currency} as of ${new Date(tenant.secondary_currency_rate_as_of).toLocaleString("en-US")}.`;
        }

        return `Secondary currency is configured for ${tenant.secondary_currency}, but no manual exchange rate has been saved yet.`;
    }, [tenant]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Finance</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Follow the live commercial path from won pipeline into quotes, invoices, and honest payment visibility.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/finance/accounting"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Accounting
                        </Link>
                        <Link
                            href="/finance/payments"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Payments
                        </Link>
                        <Link
                            href="/finance/expenses"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Expenses
                        </Link>
                        <Link
                            href="/reports/finance"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Finance Reports
                        </Link>
                        <Link
                            href="/finance/quotes/create"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Create Quote
                        </Link>
                        <Link
                            href="/finance/invoices/create"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Create Invoice
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading finance overview</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching revenue-flow reporting, recent quotes, and recent invoices from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load finance overview</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !report ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Finance overview unavailable</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        No finance reporting data is currently available for this tenant.
                    </p>
                </section>
            ) : (
                <>
                    {secondaryCurrencyNotice ? (
                        <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                            <p className="text-sm text-slate-700">{secondaryCurrencyNotice}</p>
                        </section>
                    ) : null}

                    {(report.sales_summary.currencies.length > 1 ||
                        report.summary.quote_currencies.length > 1 ||
                        report.summary.invoice_currencies.length > 1) ? (
                        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                            <p className="text-sm text-amber-900">
                                Revenue totals span multiple currencies. SupaCRM is showing truthful per-section totals without FX normalization.
                            </p>
                        </section>
                    ) : null}

                    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Open Pipeline</p>
                            <p className="mt-2 text-2xl font-semibold text-slate-900">
                                {report.sales_summary.currencies.length === 1
                                    ? formatMoney(report.sales_summary.total_open_pipeline_amount, report.sales_summary.currencies[0])
                                    : salesCurrencyLabel}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">Open deal value still moving through Sales.</p>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Weighted Pipeline</p>
                            <p className="mt-2 text-2xl font-semibold text-slate-900">
                                {report.sales_summary.currencies.length === 1
                                    ? formatMoney(report.sales_summary.weighted_pipeline_amount, report.sales_summary.currencies[0])
                                    : salesCurrencyLabel}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">Forecasted value from current deal stage weights.</p>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Quotes This Period</p>
                            <p className="mt-2 text-2xl font-semibold text-slate-900">
                                {report.summary.quote_created_this_period_count}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">Quotes created in the current 30-day reporting window.</p>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Invoices Issued</p>
                            <p className="mt-2 text-2xl font-semibold text-slate-900">
                                {report.summary.invoice_issued_count}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">Issued invoices are the strongest truthful payment visibility available today.</p>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Expense Workflow</p>
                            <p className="mt-2 text-2xl font-semibold text-slate-900">{expenseActionCount}</p>
                            <p className="mt-2 text-sm text-slate-600">
                                Submitted or approved expenses visible in the current finance workspace.
                            </p>
                        </div>
                    </section>

                    <section className="grid gap-6 xl:grid-cols-3">
                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-xl font-semibold text-slate-900">Quote Status Breakdown</h2>
                                    <p className="mt-2 text-sm text-slate-600">
                                        Quote volume and value across the live pre-invoice stages.
                                    </p>
                                </div>
                                <Link href="/finance/quotes" className="text-sm font-medium text-slate-700 underline underline-offset-2">
                                    View all quotes
                                </Link>
                            </div>

                            <div className="mt-6 space-y-3">
                                {report.quote_status_breakdown.map((item) => (
                                    <div key={item.status} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                        <div>
                                            <p className="font-medium text-slate-900">{formatStatus(item.status)}</p>
                                            <p className="text-sm text-slate-600">{item.count} quote{item.count === 1 ? "" : "s"}</p>
                                        </div>
                                        <p className="text-sm font-medium text-slate-900">{formatBreakdownAmount(item)}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-xl font-semibold text-slate-900">Invoice Status Breakdown</h2>
                                    <p className="mt-2 text-sm text-slate-600">
                                        Invoices remain the truthful payment-state source in the current repo.
                                    </p>
                                </div>
                                <Link href="/finance/invoices" className="text-sm font-medium text-slate-700 underline underline-offset-2">
                                    View all invoices
                                </Link>
                            </div>

                            <div className="mt-6 space-y-3">
                                {report.invoice_status_breakdown.map((item) => (
                                    <div key={item.status} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                        <div>
                                            <p className="font-medium text-slate-900">{formatStatus(item.status)}</p>
                                            <p className="text-sm text-slate-600">{item.count} invoice{item.count === 1 ? "" : "s"}</p>
                                        </div>
                                        <p className="text-sm font-medium text-slate-900">{formatBreakdownAmount(item)}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </section>

                    <section className="grid gap-6 xl:grid-cols-2">
                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-xl font-semibold text-slate-900">Recent Quotes</h2>
                                    <p className="mt-2 text-sm text-slate-600">
                                        Review recent quotes and move deeper into the invoice flow from the real records.
                                    </p>
                                </div>
                                <Link href="/reports/sales" className="text-sm font-medium text-slate-700 underline underline-offset-2">
                                    Open sales reporting
                                </Link>
                            </div>

                            <div className="mt-6 space-y-3">
                                {recentQuotes.length === 0 ? (
                                    <p className="text-sm text-slate-600">No quotes are available yet.</p>
                                ) : (
                                    recentQuotes.map((quote) => (
                                        <div key={quote.id} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                            <div>
                                                <Link href={`/finance/quotes/${quote.id}`} className="font-medium text-slate-900 underline underline-offset-2">
                                                    {quote.number}
                                                </Link>
                                                <p className="mt-1 text-sm text-slate-600">
                                                    {formatStatus(quote.status)} • {formatMoney(quote.total_amount, quote.currency)}
                                                </p>
                                                {getSecondaryCurrencyDisplay(tenant, quote.total_amount, quote.currency) ? (
                                                    <p className="mt-1 text-xs text-slate-500">
                                                        {getSecondaryCurrencyDisplay(tenant, quote.total_amount, quote.currency)?.convertedAmountLabel} • {getSecondaryCurrencyDisplay(tenant, quote.total_amount, quote.currency)?.rateLabel}
                                                    </p>
                                                ) : getMissingSecondaryCurrencyRateMessage(tenant, quote.currency) ? (
                                                    <p className="mt-1 text-xs text-amber-700">
                                                        {getMissingSecondaryCurrencyRateMessage(tenant, quote.currency)}
                                                    </p>
                                                ) : null}
                                            </div>
                                            <Link href={`/finance/quotes/${quote.id}`} className="text-sm font-medium text-slate-700 underline underline-offset-2">
                                                Open
                                            </Link>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-xl font-semibold text-slate-900">Recent Invoices</h2>
                                    <p className="mt-2 text-sm text-slate-600">
                                        Invoice status is the current launch-scope source of payment visibility.
                                    </p>
                                </div>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                                    Paid: {report.summary.invoice_paid_count} • Overdue: {report.summary.invoice_overdue_count}
                                </span>
                            </div>

                            <div className="mt-6 space-y-3">
                                {recentInvoices.length === 0 ? (
                                    <p className="text-sm text-slate-600">No invoices are available yet.</p>
                                ) : (
                                    recentInvoices.map((invoice) => (
                                        <div key={invoice.id} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                            <div>
                                                <Link href={`/finance/invoices/${invoice.id}`} className="font-medium text-slate-900 underline underline-offset-2">
                                                    {invoice.number}
                                                </Link>
                                                <p className="mt-1 text-sm text-slate-600">
                                                    {formatStatus(invoice.status)} • {formatMoney(invoice.total_amount, invoice.currency)}
                                                </p>
                                                {getSecondaryCurrencyDisplay(tenant, invoice.total_amount, invoice.currency) ? (
                                                    <p className="mt-1 text-xs text-slate-500">
                                                        {getSecondaryCurrencyDisplay(tenant, invoice.total_amount, invoice.currency)?.convertedAmountLabel} • {getSecondaryCurrencyDisplay(tenant, invoice.total_amount, invoice.currency)?.rateLabel}
                                                    </p>
                                                ) : getMissingSecondaryCurrencyRateMessage(tenant, invoice.currency) ? (
                                                    <p className="mt-1 text-xs text-amber-700">
                                                        {getMissingSecondaryCurrencyRateMessage(tenant, invoice.currency)}
                                                    </p>
                                                ) : null}
                                            </div>
                                            <Link href={`/finance/invoices/${invoice.id}`} className="text-sm font-medium text-slate-700 underline underline-offset-2">
                                                Open
                                            </Link>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-xl font-semibold text-slate-900">Recent Expenses</h2>
                                    <p className="mt-2 text-sm text-slate-600">
                                        Expenses stay operational until paid, then become accounting-visible through the existing journal-entry foundation.
                                    </p>
                                </div>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                                    {expenseCurrencies.length > 0 ? expenseCurrencies.join(", ") : "No expenses"}
                                </span>
                            </div>

                            <div className="mt-6 space-y-3">
                                {recentExpenses.length === 0 ? (
                                    <p className="text-sm text-slate-600">No expenses are available yet.</p>
                                ) : (
                                    recentExpenses.map((expense) => (
                                        <div key={expense.id} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 px-4 py-3">
                                            <div>
                                                <Link href="/finance/expenses" className="font-medium text-slate-900 underline underline-offset-2">
                                                    {expense.title}
                                                </Link>
                                                <p className="mt-1 text-sm text-slate-600">
                                                    {formatStatus(expense.status)} • {formatMoney(expense.amount, expense.currency)}
                                                </p>
                                                {getSecondaryCurrencyDisplay(tenant, expense.amount, expense.currency) ? (
                                                    <p className="mt-1 text-xs text-slate-500">
                                                        {getSecondaryCurrencyDisplay(tenant, expense.amount, expense.currency)?.convertedAmountLabel} • {getSecondaryCurrencyDisplay(tenant, expense.amount, expense.currency)?.rateLabel}
                                                    </p>
                                                ) : getMissingSecondaryCurrencyRateMessage(tenant, expense.currency) ? (
                                                    <p className="mt-1 text-xs text-amber-700">
                                                        {getMissingSecondaryCurrencyRateMessage(tenant, expense.currency)}
                                                    </p>
                                                ) : null}
                                            </div>
                                            <Link href="/finance/expenses" className="text-sm font-medium text-slate-700 underline underline-offset-2">
                                                Open
                                            </Link>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </section>
                </>
            )}
        </main>
    );
}

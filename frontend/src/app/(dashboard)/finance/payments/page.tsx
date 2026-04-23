"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getCompanies } from "@/services/companies.service";
import { getInvoices } from "@/services/invoices.service";
import { getPayments } from "@/services/payments.service";
import type { Company } from "@/types/crm";
import type { Invoice } from "@/types/finance";
import type { InvoicePayment, PaymentMethod, PaymentStatus } from "@/types/payments";

type PaymentsSnapshot = {
    payments: InvoicePayment[];
    invoices: Invoice[];
    companies: Company[];
};

const STATUS_FILTER_OPTIONS: Array<{ value: "" | PaymentStatus; label: string }> = [
    { value: "", label: "All statuses" },
    { value: "completed", label: "Completed" },
    { value: "pending", label: "Pending" },
    { value: "failed", label: "Failed" },
    { value: "cancelled", label: "Cancelled" },
];

const METHOD_FILTER_OPTIONS: Array<{ value: "" | PaymentMethod; label: string }> = [
    { value: "", label: "All methods" },
    { value: "bank_transfer", label: "Bank transfer" },
    { value: "cash", label: "Cash" },
    { value: "card_manual", label: "Card manual" },
    { value: "other", label: "Other" },
];

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

async function loadPaymentsSnapshot(
    invoiceId: string,
    status: "" | PaymentStatus,
    method: "" | PaymentMethod,
): Promise<PaymentsSnapshot> {
    const [paymentsResponse, invoicesResponse, companiesResponse] = await Promise.all([
        getPayments({
            invoice_id: invoiceId || undefined,
            status: status || undefined,
            method: method || undefined,
            limit: 100,
            offset: 0,
        }),
        getInvoices({ limit: 200, offset: 0 }),
        getCompanies(),
    ]);

    return {
        payments: paymentsResponse.items ?? [],
        invoices: invoicesResponse.items ?? [],
        companies: companiesResponse.items ?? [],
    };
}

export default function PaymentsPage() {
    const searchParams = useSearchParams();
    const [snapshot, setSnapshot] = useState<PaymentsSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [statusFilter, setStatusFilter] = useState<"" | PaymentStatus>("");
    const [methodFilter, setMethodFilter] = useState<"" | PaymentMethod>("");

    const invoiceFilter = searchParams.get("invoice_id") ?? "";

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");
            const nextSnapshot = await loadPaymentsSnapshot(invoiceFilter, statusFilter, methodFilter);
            setSnapshot(nextSnapshot);
        } catch (error) {
            console.error("Failed to load payments page:", error);
            setErrorMessage(
                parseApiError(error, "The payments workspace could not be loaded from the backend."),
            );
            setSnapshot(null);
        } finally {
            setIsLoading(false);
        }
    }, [invoiceFilter, methodFilter, statusFilter]);

    useEffect(() => {
        void loadSnapshot();
    }, [loadSnapshot]);

    const metrics = useMemo(() => {
        const payments = snapshot?.payments ?? [];
        const currencies = new Set(payments.map((payment) => payment.currency));
        const completed = payments.filter((payment) => payment.status === "completed");
        const pending = payments.filter((payment) => payment.status === "pending");
        const completedAmount = completed.reduce((sum, payment) => sum + Number(payment.amount || "0"), 0);
        return {
            paymentCount: payments.length,
            completedCount: completed.length,
            pendingCount: pending.length,
            currencies: Array.from(currencies).sort(),
            completedAmount,
        };
    }, [snapshot]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Payments</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Review invoice-linked payment records without implying live gateway connectivity.
                        </p>
                        {invoiceFilter ? (
                            <p className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                                Filtered to invoice {invoiceFilter}.
                            </p>
                        ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/finance/payments/gateway-settings"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Gateway Settings
                        </Link>
                        <Link
                            href="/finance/payments/integrations"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Integrations
                        </Link>
                        <Link
                            href="/finance/payments/subscription-billing"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Subscription Billing
                        </Link>
                        <Link
                            href="/finance"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to Finance
                        </Link>
                        <Link
                            href="/reports/finance"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Open Finance Reports
                        </Link>
                    </div>
                </div>

                <div className="mt-6 grid gap-3 md:grid-cols-2">
                    <select
                        value={statusFilter}
                        onChange={(event) => setStatusFilter(event.target.value as "" | PaymentStatus)}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    >
                        {STATUS_FILTER_OPTIONS.map((option) => (
                            <option key={option.label} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>

                    <select
                        value={methodFilter}
                        onChange={(event) => setMethodFilter(event.target.value as "" | PaymentMethod)}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    >
                        {METHOD_FILTER_OPTIONS.map((option) => (
                            <option key={option.label} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading payments</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching payment records, invoices, and company context from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load payments</h2>
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
                    {metrics.currencies.length > 1 ? (
                        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                            <p className="text-sm text-amber-900">
                                Payment records currently span multiple currencies ({metrics.currencies.join(", ")}) and are shown without FX normalization.
                            </p>
                        </section>
                    ) : null}

                    <section className="grid gap-4 md:grid-cols-3">
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recorded payments</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{metrics.paymentCount}</p>
                            <p className="mt-2 text-sm text-slate-600">Across the current tenant and active filters.</p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Completed receipts</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {metrics.currencies.length === 1
                                    ? formatMoney(String(metrics.completedAmount.toFixed(2)), metrics.currencies[0])
                                    : "Mixed currencies"}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">{metrics.completedCount} completed payments.</p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Pending</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{metrics.pendingCount}</p>
                            <p className="mt-2 text-sm text-slate-600">Saved but not completed.</p>
                        </article>
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Payment records</h2>
                        <div className="mt-6 space-y-3">
                            {snapshot.payments.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                    No payment records match the current filters.
                                </div>
                            ) : (
                                snapshot.payments.map((payment) => {
                                    const invoice = snapshot.invoices.find((item) => item.id === payment.invoice_id);
                                    const company = invoice
                                        ? snapshot.companies.find((item) => item.id === invoice.company_id)
                                        : null;

                                    return (
                                        <div key={payment.id} className="rounded-lg border border-slate-200 px-4 py-4">
                                            <div className="flex flex-wrap items-start justify-between gap-4">
                                                <div>
                                                    <p className="font-medium text-slate-900">
                                                        {formatLabel(payment.method)} · {formatLabel(payment.status)}
                                                    </p>
                                                    <p className="mt-1 text-sm text-slate-600">
                                                        {formatDateTime(payment.payment_date)}
                                                    </p>
                                                    <div className="mt-2 flex flex-wrap gap-3 text-sm text-slate-600">
                                                        <Link
                                                            href={`/finance/invoices/${payment.invoice_id}`}
                                                            className="underline underline-offset-2"
                                                        >
                                                            {invoice?.number ?? payment.invoice_id}
                                                        </Link>
                                                        {company ? <span>{company.name}</span> : null}
                                                    </div>
                                                </div>
                                                <p className="text-sm font-medium text-slate-900">
                                                    {formatMoney(payment.amount, payment.currency)}
                                                </p>
                                            </div>
                                            {payment.external_reference ? (
                                                <p className="mt-3 text-sm text-slate-600">
                                                    Reference: {payment.external_reference}
                                                </p>
                                            ) : null}
                                            {payment.notes ? (
                                                <p className="mt-2 text-sm text-slate-600">{payment.notes}</p>
                                            ) : null}
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </section>
                </>
            ) : null}
        </main>
    );
}

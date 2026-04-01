"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import InvoicesList from "@/components/finance/InvoicesList";
import { useAuth } from "@/hooks/use-auth";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getInvoices } from "@/services/invoices.service";
import { getProducts } from "@/services/products.service";
import type { Company, Contact } from "@/types/crm";
import type { Invoice, InvoiceStatus } from "@/types/finance";
import type { Product } from "@/types/product";

const STATUS_FILTER_OPTIONS: Array<{ value: "" | InvoiceStatus; label: string }> = [
    { value: "", label: "All statuses" },
    { value: "draft", label: "Draft" },
    { value: "issued", label: "Issued" },
    { value: "paid", label: "Paid" },
    { value: "overdue", label: "Overdue" },
    { value: "cancelled", label: "Cancelled" },
];

type InvoiceMetrics = {
    totalInvoices: number;
    draftCount: number;
    issuedCount: number;
    paidCount: number;
    overdueCount: number;
    cancelledCount: number;
    totalInvoicedAmount: number;
    totalPaidAmount: number;
    hasMixedCurrencies: boolean;
    sharedCurrency: string | null;
};

function formatMoney(amount: number, currency: string): string {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(amount);
}

export default function InvoicesPage() {
    const auth = useAuth();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [total, setTotal] = useState<number>(0);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [statusFilter, setStatusFilter] = useState<"" | InvoiceStatus>("");
    const [companyFilter, setCompanyFilter] = useState<string>("");
    const [invoiceNumberSearch, setInvoiceNumberSearch] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            return;
        }

        let isMounted = true;

        async function loadReferenceData(): Promise<void> {
            try {
                const [companiesResponse, contactsResponse, productsResponse] =
                    await Promise.all([
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                    ]);

                if (!isMounted) {
                    return;
                }

                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setProducts(productsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load invoice reference data:", error);
            }
        }

        void loadReferenceData();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    const loadInvoices = useCallback(async (): Promise<void> => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        try {
            setIsLoading(true);
            setErrorMessage("");

            const response = await getInvoices({
                status: statusFilter || undefined,
                company_id: companyFilter || undefined,
                number: invoiceNumberSearch.trim() || undefined,
            });

            setInvoices(response.items ?? []);
            setTotal(response.total ?? 0);
        } catch (error) {
            console.error("Failed to load invoices page:", error);
            setErrorMessage("The invoices page could not be loaded from the backend.");
        } finally {
            setIsLoading(false);
        }
    }, [
        auth.accessToken,
        auth.isAuthenticated,
        auth.isReady,
        companyFilter,
        invoiceNumberSearch,
        statusFilter,
    ]);

    useEffect(() => {
        void loadInvoices();
    }, [loadInvoices]);

    const hasActiveFilters = useMemo(() => {
        return Boolean(statusFilter || companyFilter || invoiceNumberSearch.trim());
    }, [companyFilter, invoiceNumberSearch, statusFilter]);

    const metrics = useMemo<InvoiceMetrics>(() => {
        let draftCount = 0;
        let issuedCount = 0;
        let paidCount = 0;
        let overdueCount = 0;
        let cancelledCount = 0;
        let totalInvoicedAmount = 0;
        let totalPaidAmount = 0;
        let sharedCurrency: string | null = null;
        let hasMixedCurrencies = false;

        for (const invoice of invoices) {
            if (invoice.status === "draft") {
                draftCount += 1;
            } else if (invoice.status === "issued") {
                issuedCount += 1;
            } else if (invoice.status === "paid") {
                paidCount += 1;
            } else if (invoice.status === "overdue") {
                overdueCount += 1;
            } else if (invoice.status === "cancelled") {
                cancelledCount += 1;
            }

            const normalizedCurrency = invoice.currency.trim().toUpperCase();
            if (!sharedCurrency) {
                sharedCurrency = normalizedCurrency;
            } else if (sharedCurrency !== normalizedCurrency) {
                hasMixedCurrencies = true;
            }

            const parsedAmount = Number(invoice.total_amount);
            if (!Number.isFinite(parsedAmount)) {
                continue;
            }

            totalInvoicedAmount += parsedAmount;

            if (invoice.status === "paid") {
                totalPaidAmount += parsedAmount;
            }
        }

        return {
            totalInvoices: invoices.length,
            draftCount,
            issuedCount,
            paidCount,
            overdueCount,
            cancelledCount,
            totalInvoicedAmount,
            totalPaidAmount,
            hasMixedCurrencies,
            sharedCurrency,
        };
    }, [invoices]);

    const totalInvoicedAmountLabel = useMemo(() => {
        if (metrics.totalInvoices === 0) {
            return "0";
        }

        if (metrics.hasMixedCurrencies || !metrics.sharedCurrency) {
            return "Mixed currencies";
        }

        return formatMoney(metrics.totalInvoicedAmount, metrics.sharedCurrency);
    }, [metrics]);

    const totalPaidAmountLabel = useMemo(() => {
        if (metrics.totalInvoices === 0) {
            return "0";
        }

        if (metrics.hasMixedCurrencies || !metrics.sharedCurrency) {
            return "Mixed currencies";
        }

        return formatMoney(metrics.totalPaidAmount, metrics.sharedCurrency);
    }, [metrics]);

    function clearFilters(): void {
        setStatusFilter("");
        setCompanyFilter("");
        setInvoiceNumberSearch("");
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">All Invoices</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Filter and review invoices stored in your finance module.
                </p>

                <div className="mt-6 grid gap-3 md:grid-cols-3">
                    <input
                        type="text"
                        value={invoiceNumberSearch}
                        onChange={(event) => setInvoiceNumberSearch(event.target.value)}
                        placeholder="Search invoice number (e.g. INV-000004)"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />

                    <select
                        value={statusFilter}
                        onChange={(event) =>
                            setStatusFilter(event.target.value as "" | InvoiceStatus)
                        }
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    >
                        {STATUS_FILTER_OPTIONS.map((option) => (
                            <option key={option.label} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>

                    <select
                        value={companyFilter}
                        onChange={(event) => setCompanyFilter(event.target.value)}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    >
                        <option value="">All companies</option>
                        {companies.map((company) => (
                            <option key={company.id} value={company.id}>
                                {company.name}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="mt-4">
                    <button
                        type="button"
                        onClick={clearFilters}
                        disabled={!hasActiveFilters}
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        Clear filters
                    </button>
                </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h2 className="text-xl font-semibold text-slate-900">Invoice Metrics</h2>
                <p className="mt-2 text-sm text-slate-600">
                    Metrics are calculated from the currently loaded invoice dataset.
                </p>

                <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Invoices</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.totalInvoices}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Draft</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.draftCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Issued</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.issuedCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Paid</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.paidCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Overdue</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.overdueCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Cancelled</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.cancelledCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Invoiced Amount</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{totalInvoicedAmountLabel}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Paid Amount</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{totalPaidAmountLabel}</p>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Loading invoices
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching invoices, companies, contacts, and products from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">
                        Failed to load invoices
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : invoices.length === 0 ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        No invoices found
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        {hasActiveFilters
                            ? "No invoices match your current filters."
                            : "No invoices available yet."}
                    </p>
                </section>
            ) : (
                <InvoicesList
                    invoices={invoices}
                    total={total}
                    companies={companies}
                    contacts={contacts}
                    products={products}
                    onStatusUpdated={loadInvoices}
                />
            )}
        </main>
    );
}

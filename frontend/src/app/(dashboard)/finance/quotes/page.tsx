"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import QuotesList from "@/components/finance/QuotesList";
import { useAuth } from "@/hooks/use-auth";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals } from "@/services/deals.service";
import { getProducts } from "@/services/products.service";
import { getQuotes } from "@/services/quotes.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Quote, QuoteStatus } from "@/types/finance";
import type { Product } from "@/types/product";

const STATUS_FILTER_OPTIONS: Array<{ value: "" | QuoteStatus; label: string }> = [
    { value: "", label: "All statuses" },
    { value: "draft", label: "Draft" },
    { value: "sent", label: "Sent" },
    { value: "accepted", label: "Accepted" },
    { value: "rejected", label: "Rejected" },
    { value: "expired", label: "Expired" },
];

type QuoteMetrics = {
    totalQuotes: number;
    draftCount: number;
    sentCount: number;
    acceptedCount: number;
    rejectedCount: number;
    expiredCount: number;
    totalQuotedAmount: number;
    totalAcceptedAmount: number;
    hasMixedCurrencies: boolean;
    sharedCurrency: string | null;
};

function formatMoney(amount: number, currency: string): string {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(amount);
}

export default function QuotesPage() {
    const auth = useAuth();
    const [quotes, setQuotes] = useState<Quote[]>([]);
    const [total, setTotal] = useState<number>(0);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [deals, setDeals] = useState<Deal[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [statusFilter, setStatusFilter] = useState<"" | QuoteStatus>("");
    const [companyFilter, setCompanyFilter] = useState<string>("");
    const [quoteNumberSearch, setQuoteNumberSearch] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
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

                let dealsItems: Deal[] = [];
                try {
                    const dealsResponse = await getDeals();
                    dealsItems = dealsResponse.items ?? [];
                } catch (error) {
                    console.warn("Deals could not be loaded for quote list enrichment:", error);
                }

                if (!isMounted) {
                    return;
                }

                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setDeals(dealsItems);
                setProducts(productsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load quote reference data:", error);
            }
        }

        void loadReferenceData();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    const loadQuotes = useCallback(async (): Promise<void> => {
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

            const response = await getQuotes({
                status: statusFilter || undefined,
                company_id: companyFilter || undefined,
                number: quoteNumberSearch.trim() || undefined,
            });

            setQuotes(response.items ?? []);
            setTotal(response.total ?? 0);
        } catch (error) {
            console.error("Failed to load quotes page data:", error);
            setErrorMessage("The quotes page could not be loaded from the backend.");
        } finally {
            setIsLoading(false);
        }
    }, [
        auth.accessToken,
        auth.isAuthenticated,
        auth.isReady,
        companyFilter,
        quoteNumberSearch,
        statusFilter,
    ]);

    useEffect(() => {
        void loadQuotes();
    }, [loadQuotes]);

    const hasActiveFilters = useMemo(() => {
        return Boolean(statusFilter || companyFilter || quoteNumberSearch.trim());
    }, [companyFilter, quoteNumberSearch, statusFilter]);

    const metrics = useMemo<QuoteMetrics>(() => {
        let draftCount = 0;
        let sentCount = 0;
        let acceptedCount = 0;
        let rejectedCount = 0;
        let expiredCount = 0;
        let totalQuotedAmount = 0;
        let totalAcceptedAmount = 0;
        let sharedCurrency: string | null = null;
        let hasMixedCurrencies = false;

        for (const quote of quotes) {
            if (quote.status === "draft") {
                draftCount += 1;
            } else if (quote.status === "sent") {
                sentCount += 1;
            } else if (quote.status === "accepted") {
                acceptedCount += 1;
            } else if (quote.status === "rejected") {
                rejectedCount += 1;
            } else if (quote.status === "expired") {
                expiredCount += 1;
            }

            const normalizedCurrency = quote.currency.trim().toUpperCase();
            if (!sharedCurrency) {
                sharedCurrency = normalizedCurrency;
            } else if (sharedCurrency !== normalizedCurrency) {
                hasMixedCurrencies = true;
            }

            const parsedAmount = Number(quote.total_amount);
            if (!Number.isFinite(parsedAmount)) {
                continue;
            }

            totalQuotedAmount += parsedAmount;

            if (quote.status === "accepted") {
                totalAcceptedAmount += parsedAmount;
            }
        }

        return {
            totalQuotes: quotes.length,
            draftCount,
            sentCount,
            acceptedCount,
            rejectedCount,
            expiredCount,
            totalQuotedAmount,
            totalAcceptedAmount,
            hasMixedCurrencies,
            sharedCurrency,
        };
    }, [quotes]);

    const totalQuotedAmountLabel = useMemo(() => {
        if (metrics.totalQuotes === 0) {
            return "0";
        }

        if (metrics.hasMixedCurrencies || !metrics.sharedCurrency) {
            return "Mixed currencies";
        }

        return formatMoney(metrics.totalQuotedAmount, metrics.sharedCurrency);
    }, [metrics]);

    const totalAcceptedAmountLabel = useMemo(() => {
        if (metrics.totalQuotes === 0) {
            return "0";
        }

        if (metrics.hasMixedCurrencies || !metrics.sharedCurrency) {
            return "Mixed currencies";
        }

        return formatMoney(metrics.totalAcceptedAmount, metrics.sharedCurrency);
    }, [metrics]);

    function clearFilters(): void {
        setStatusFilter("");
        setCompanyFilter("");
        setQuoteNumberSearch("");
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">All Quotes</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Review customer quotes and estimates before invoicing.
                        </p>
                    </div>

                    <Link
                        href="/finance/quotes/create"
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                    >
                        Create Quote
                    </Link>
                </div>

                <div className="mt-6 grid gap-3 md:grid-cols-3">
                    <input
                        type="text"
                        value={quoteNumberSearch}
                        onChange={(event) => setQuoteNumberSearch(event.target.value)}
                        placeholder="Search quote number (e.g. QTE-000001)"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />

                    <select
                        value={statusFilter}
                        onChange={(event) =>
                            setStatusFilter(event.target.value as "" | QuoteStatus)
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
                <h2 className="text-xl font-semibold text-slate-900">Quote Metrics</h2>
                <p className="mt-2 text-sm text-slate-600">
                    Metrics are calculated from the currently loaded quote dataset.
                </p>

                <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Quotes</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.totalQuotes}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Draft</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.draftCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sent</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.sentCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Accepted</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.acceptedCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Rejected</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.rejectedCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Expired</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{metrics.expiredCount}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Quoted Amount</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{totalQuotedAmountLabel}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Accepted Amount</p>
                        <p className="mt-1 text-2xl font-semibold text-slate-900">{totalAcceptedAmountLabel}</p>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Loading quotes
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching quotes, companies, contacts, deals, and products from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">
                        Failed to load quotes
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : quotes.length === 0 ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        No quotes found
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        {hasActiveFilters
                            ? "No quotes match your current filters."
                            : "Create your first quote to start estimating deals."}
                    </p>
                </section>
            ) : (
                <QuotesList
                    quotes={quotes}
                    total={total}
                    companies={companies}
                    contacts={contacts}
                    deals={deals}
                    products={products}
                    onStatusUpdated={loadQuotes}
                />
            )}
        </main>
    );
}

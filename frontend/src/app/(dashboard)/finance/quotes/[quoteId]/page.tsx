"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals } from "@/services/deals.service";
import { getProducts } from "@/services/products.service";
import { convertQuoteToInvoice, deleteQuote, getQuoteById } from "@/services/quotes.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Quote } from "@/types/finance";
import type { Product } from "@/types/product";

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

function formatStatus(status: string): string {
    return status
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function getLoadErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Quote not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The quote could not be loaded from the backend.";
}

function getDeleteErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Quote not found. It may have already been deleted.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The quote could not be deleted.";
}

function getConvertErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Quote not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The quote could not be converted to an invoice.";
}

function getCompanyName(companies: Company[], companyId: string): string {
    return companies.find((company) => company.id === companyId)?.name ?? companyId;
}

function getContactName(contacts: Contact[], contactId: string | null): string {
    if (!contactId) {
        return "No contact";
    }

    const contact = contacts.find((item) => item.id === contactId);
    if (!contact) {
        return contactId;
    }

    return `${contact.first_name} ${contact.last_name ?? ""}`.trim();
}

function getDealName(deals: Deal[], dealId: string | null): string {
    if (!dealId) {
        return "No deal";
    }

    const deal = deals.find((item) => item.id === dealId);
    if (!deal) {
        return dealId;
    }

    return deal.name;
}

function getProductName(products: Product[], productId: string | null): string {
    if (!productId) {
        return "No product";
    }

    const product = products.find((item) => item.id === productId);
    if (!product) {
        return productId;
    }

    return product.name;
}

export default function QuoteDetailPage() {
    const auth = useAuth();
    const router = useRouter();
    const params = useParams<{ quoteId: string }>();
    const rawQuoteId = params?.quoteId;
    const quoteId = Array.isArray(rawQuoteId) ? rawQuoteId[0] : rawQuoteId;
    const convertLockRef = useRef<boolean>(false);

    const [quote, setQuote] = useState<Quote | null>(null);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [deals, setDeals] = useState<Deal[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState<boolean>(false);
    const [isDeleting, setIsDeleting] = useState<boolean>(false);
    const [deleteError, setDeleteError] = useState<string>("");
    const [isConverting, setIsConverting] = useState<boolean>(false);
    const [convertError, setConvertError] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        if (!quoteId) {
            setErrorMessage("Invalid quote id.");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadQuoteDetail(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const [quoteResponse, companiesResponse, contactsResponse, productsResponse] =
                    await Promise.all([
                        getQuoteById(quoteId),
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                    ]);

                let dealsItems: Deal[] = [];
                try {
                    const dealsResponse = await getDeals();
                    dealsItems = dealsResponse.items ?? [];
                } catch (error) {
                    console.warn("Deals could not be loaded for quote detail enrichment:", error);
                }

                if (!isMounted) {
                    return;
                }

                setQuote(quoteResponse);
                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setDeals(dealsItems);
                setProducts(productsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load quote detail:", error);

                if (!isMounted) {
                    return;
                }

                setErrorMessage(getLoadErrorMessage(error));
                setQuote(null);
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadQuoteDetail();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, quoteId]);

    async function handleDeleteConfirmed(): Promise<void> {
        if (!quoteId || isDeleting || isConverting) {
            return;
        }

        try {
            setDeleteError("");
            setIsDeleting(true);

            await deleteQuote(quoteId);

            router.push("/finance/quotes");
            router.refresh();
        } catch (error) {
            console.error("Failed to delete quote:", error);
            setDeleteError(getDeleteErrorMessage(error));
        } finally {
            setIsDeleting(false);
        }
    }

    async function handleConvertToInvoice(): Promise<void> {
        if (!quoteId || !quote || isConverting || isDeleting || convertLockRef.current) {
            return;
        }

        try {
            convertLockRef.current = true;
            setConvertError("");
            setIsConverting(true);

            const invoice = await convertQuoteToInvoice(quoteId);

            router.push(`/finance/invoices/${invoice.id}`);
            router.refresh();
        } catch (error) {
            console.error("Failed to convert quote to invoice:", error);
            setConvertError(getConvertErrorMessage(error));
        } finally {
            convertLockRef.current = false;
            setIsConverting(false);
        }
    }

    const detailRows = useMemo(() => {
        if (!quote) {
            return [];
        }

        return [
            { label: "Quote Number", value: quote.number },
            { label: "Company", value: getCompanyName(companies, quote.company_id) },
            { label: "Contact", value: getContactName(contacts, quote.contact_id) },
            { label: "Deal", value: getDealName(deals, quote.deal_id) },
            { label: "Product", value: getProductName(products, quote.product_id) },
            { label: "Issue Date", value: formatDate(quote.issue_date) },
            { label: "Expiry Date", value: formatDate(quote.expiry_date) },
            { label: "Currency", value: quote.currency },
            { label: "Total Amount", value: formatMoney(quote.total_amount, quote.currency) },
            { label: "Status", value: formatStatus(quote.status) },
            { label: "Notes", value: quote.notes?.trim() ? quote.notes : "No notes" },
            { label: "Created At", value: formatDateTime(quote.created_at) },
            { label: "Updated At", value: formatDateTime(quote.updated_at) },
        ];
    }, [companies, contacts, deals, products, quote]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">
                            {quote ? quote.number : "Quote Details"}
                        </h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Read-only quote details.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {quote?.status === "accepted" ? (
                            <button
                                type="button"
                                onClick={() => {
                                    void handleConvertToInvoice();
                                }}
                                disabled={isConverting || isDeleting}
                                className="rounded-lg border border-emerald-300 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                {isConverting ? "Converting..." : "Convert to invoice"}
                            </button>
                        ) : null}
                        <Link
                            href={quoteId ? `/finance/quotes/${quoteId}/edit` : "/finance/quotes"}
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Edit quote
                        </Link>
                        <Link
                            href="/finance/quotes"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all quotes
                        </Link>
                        {quote ? (
                            <button
                                type="button"
                                onClick={() => {
                                    setDeleteError("");
                                    setIsDeleteConfirmOpen(true);
                                }}
                                disabled={isDeleting || isConverting}
                                className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                {isDeleting ? "Deleting..." : "Delete quote"}
                            </button>
                        ) : null}
                    </div>
                </div>

                {convertError ? (
                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
                        <p className="text-sm text-red-700">{convertError}</p>
                    </div>
                ) : null}

                {isDeleteConfirmOpen && quote ? (
                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
                        <p className="text-sm font-medium text-red-800">
                            Are you sure you want to delete {quote.number}?
                        </p>
                        <p className="mt-1 text-sm text-red-700">
                            This action cannot be undone.
                        </p>

                        <div className="mt-3 flex flex-wrap gap-2">
                            <button
                                type="button"
                                onClick={() => {
                                    void handleDeleteConfirmed();
                                }}
                                disabled={isDeleting}
                                className="rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                {isDeleting ? "Deleting..." : "Yes, delete quote"}
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    if (isDeleting) {
                                        return;
                                    }
                                    setIsDeleteConfirmOpen(false);
                                    setDeleteError("");
                                }}
                                disabled={isDeleting}
                                className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                Cancel
                            </button>
                        </div>

                        {deleteError ? (
                            <p className="mt-3 text-sm text-red-700">{deleteError}</p>
                        ) : null}
                    </div>
                ) : null}
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Loading quote details
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching quote, company, contact, deal, and product data from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">
                        Failed to load quote
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !quote ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Quote unavailable
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested quote could not be found.
                    </p>
                </section>
            ) : (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <div className="grid gap-4 md:grid-cols-2">
                        {detailRows.map((row) => (
                            <div key={row.label} className="rounded-lg border border-slate-200 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                    {row.label}
                                </p>
                                <p className="mt-1 text-sm text-slate-900">{row.value}</p>
                            </div>
                        ))}
                    </div>
                </section>
            )}
        </main>
    );
}

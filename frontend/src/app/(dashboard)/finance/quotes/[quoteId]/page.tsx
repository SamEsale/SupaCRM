"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import {
    getMissingSecondaryCurrencyRateMessage,
    getSecondaryCurrencyDisplay,
} from "@/lib/finance-currency";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals } from "@/services/deals.service";
import { getInvoices } from "@/services/invoices.service";
import { getProducts } from "@/services/products.service";
import { convertQuoteToInvoice, deleteQuote, getQuoteById } from "@/services/quotes.service";
import { getCurrentTenant } from "@/services/tenants.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Quote } from "@/types/finance";
import type { Product } from "@/types/product";
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

function buildCompanyValue(companies: Company[], companyId: string): ReactNode {
    const companyName = getCompanyName(companies, companyId);

    return (
        <Link
            href={`/companies/${companyId}`}
            className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
        >
            {companyName}
        </Link>
    );
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

function buildContactValue(contacts: Contact[], contactId: string | null): ReactNode {
    if (!contactId) {
        return "No contact";
    }

    return (
        <Link
            href={`/contacts/${contactId}`}
            className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
        >
            {getContactName(contacts, contactId)}
        </Link>
    );
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

function buildDealValue(deals: Deal[], dealId: string | null): ReactNode {
    if (!dealId) {
        return "No deal";
    }

    return (
        <Link
            href={`/deals/${dealId}`}
            className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
        >
            {getDealName(deals, dealId)}
        </Link>
    );
}

function buildSourceDealValue(
    deals: Deal[],
    sourceDealId: string | null,
): ReactNode {
    if (!sourceDealId) {
        return "Not created from a deal";
    }

    const sourceDealName = getDealName(deals, sourceDealId);

    return (
        <span>
            <span className="font-medium text-slate-900">{sourceDealName}</span>
            {sourceDealName !== sourceDealId ? (
                <span className="ml-1 text-slate-500">({sourceDealId})</span>
            ) : null}
            <span className="ml-2 text-slate-500">-</span>{" "}
            <Link
                href={`/deals/${sourceDealId}`}
                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
            >
                View deal
            </Link>
        </span>
    );
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

function buildProductValue(products: Product[], productId: string | null): ReactNode {
    if (!productId) {
        return "No product";
    }

    return (
        <Link
            href={`/products/${productId}`}
            className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
        >
            {getProductName(products, productId)}
        </Link>
    );
}

export default function QuoteDetailPage() {
    const auth = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const params = useParams<{ quoteId: string }>();
    const rawQuoteId = params?.quoteId;
    const quoteId = Array.isArray(rawQuoteId) ? rawQuoteId[0] : rawQuoteId;
    const convertLockRef = useRef<boolean>(false);

    const [quote, setQuote] = useState<Quote | null>(null);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [deals, setDeals] = useState<Deal[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [tenant, setTenant] = useState<Tenant | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState<boolean>(false);
    const [isDeleting, setIsDeleting] = useState<boolean>(false);
    const [deleteError, setDeleteError] = useState<string>("");
    const [isConverting, setIsConverting] = useState<boolean>(false);
    const [convertError, setConvertError] = useState<string>("");
    const [linkedInvoices, setLinkedInvoices] = useState<Array<{ id: string; number: string; status: string; total_amount: string; currency: string }>>([]);

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

                const [quoteResponse, companiesResponse, contactsResponse, productsResponse, tenantResponse] =
                    await Promise.all([
                        getQuoteById(quoteId),
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                        getCurrentTenant(),
                    ]);

                let dealsItems: Deal[] = [];
                try {
                    const dealsResponse = await getDeals();
                    dealsItems = dealsResponse.items ?? [];
                } catch (error) {
                    console.warn("Deals could not be loaded for quote detail enrichment:", error);
                }

                let resolvedInvoices: Array<{ id: string; number: string; status: string; total_amount: string; currency: string }> = [];
                try {
                    const linkedInvoices = await getInvoices({
                        source_quote_id: quoteId,
                        limit: 20,
                        offset: 0,
                    });
                    resolvedInvoices = linkedInvoices.items ?? [];
                } catch (error) {
                    console.warn("Linked invoice data could not be loaded for quote detail:", error);
                }

                if (!isMounted) {
                    return;
                }

                setQuote(quoteResponse);
                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setDeals(dealsItems);
                setProducts(productsResponse.items ?? []);
                setTenant(tenantResponse);
                setLinkedInvoices(resolvedInvoices);
            } catch (error) {
                console.error("Failed to load quote detail:", error);

                if (!isMounted) {
                    return;
                }

                setErrorMessage(getLoadErrorMessage(error));
                setQuote(null);
                setTenant(null);
                setLinkedInvoices([]);
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

    const linkedInvoiceCount = linkedInvoices.length;
    const linkedInvoiceId = linkedInvoices[0]?.id ?? null;
    const createdFromDeal = searchParams.get("createdFrom") === "deal";
    const convertedAmount = quote
        ? getSecondaryCurrencyDisplay(tenant, quote.total_amount, quote.currency)
        : null;
    const missingRateMessage = quote
        ? getMissingSecondaryCurrencyRateMessage(tenant, quote.currency)
        : null;

    const detailRows = useMemo(() => {
        if (!quote) {
            return [];
        }

        const sourceDealValue = buildSourceDealValue(deals, quote.source_deal_id);

        return [
            { label: "Quote Number", value: quote.number },
            { label: "Company", value: buildCompanyValue(companies, quote.company_id) },
            { label: "Contact", value: buildContactValue(contacts, quote.contact_id) },
            { label: "Deal", value: buildDealValue(deals, quote.deal_id) },
            { label: "Source Deal", value: sourceDealValue },
            { label: "Product", value: buildProductValue(products, quote.product_id) },
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
                        {createdFromDeal ? (
                            <p className="mt-2 text-sm text-emerald-700">
                                Quote created successfully from the originating deal context.
                            </p>
                        ) : null}
                        {linkedInvoiceCount > 0 ? (
                            <p className="mt-2 text-sm text-emerald-700">
                                This quote has already been converted to{" "}
                                {linkedInvoiceCount === 1
                                    ? "1 invoice"
                                    : `${linkedInvoiceCount} invoices`}
                                .
                            </p>
                        ) : null}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {quote?.status === "accepted" ? (
                            linkedInvoiceId ? (
                                <Link
                                    href={`/finance/invoices/${linkedInvoiceId}`}
                                    className="rounded-lg border border-emerald-300 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50"
                                >
                                    View converted invoice
                                </Link>
                            ) : linkedInvoiceCount > 0 ? (
                                <span className="rounded-lg border border-emerald-300 px-4 py-2 text-sm font-medium text-emerald-700">
                                    Already converted
                                </span>
                            ) : (
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
                            )
                        ) : null}
                        {quote?.status === "accepted" ? (
                            <Link
                                href={`/finance/invoices/create?source_quote_id=${quote.id}`}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                            >
                                Open invoice form
                            </Link>
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
                <>
                    {convertedAmount || missingRateMessage ? (
                        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <h2 className="text-lg font-semibold text-slate-900">Currency context</h2>
                            {convertedAmount ? (
                                <>
                                    <p className="mt-2 text-sm text-slate-700">
                                        Secondary currency view: {convertedAmount.convertedAmountLabel}
                                    </p>
                                    <p className="mt-2 text-sm text-slate-600">
                                        {convertedAmount.rateLabel} • {convertedAmount.sourceLabel} • {convertedAmount.asOfLabel}
                                    </p>
                                </>
                            ) : (
                                <p className="mt-2 text-sm text-amber-700">{missingRateMessage}</p>
                            )}
                        </section>
                    ) : null}

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

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h2 className="text-xl font-semibold text-slate-900">Related invoices</h2>
                                <p className="mt-2 text-sm text-slate-600">
                                    Invoice linkage is derived from this quote through the existing commercial flow.
                                </p>
                            </div>
                            {linkedInvoiceId ? (
                                <Link
                                    href={`/finance/invoices/${linkedInvoiceId}`}
                                    className="rounded-lg border border-emerald-300 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50"
                                >
                                    Open latest invoice
                                </Link>
                            ) : null}
                        </div>

                        {linkedInvoices.length === 0 ? (
                            <p className="mt-6 text-sm text-slate-600">
                                No invoices have been created from this quote yet.
                            </p>
                        ) : (
                            <div className="mt-6 space-y-3">
                                {linkedInvoices.map((invoice) => (
                                    <div
                                        key={invoice.id}
                                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 px-4 py-3"
                                    >
                                        <div>
                                            <Link
                                                href={`/finance/invoices/${invoice.id}`}
                                                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
                                            >
                                                {invoice.number}
                                            </Link>
                                            <p className="mt-1 text-sm text-slate-600">
                                                {formatMoney(invoice.total_amount, invoice.currency)} • {formatStatus(invoice.status)}
                                            </p>
                                        </div>
                                        <Link
                                            href={`/finance/invoices/${invoice.id}`}
                                            className="text-sm font-medium text-slate-700 underline underline-offset-2"
                                        >
                                            View invoice
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                </>
            )}
        </main>
    );
}

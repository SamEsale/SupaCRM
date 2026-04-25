"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useEffect, useMemo, useState } from "react";

import DealFollowUpCard from "@/components/deals/DealFollowUpCard";
import { useAuth } from "@/hooks/use-auth";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { deleteDeal, getDealById } from "@/services/deals.service";
import { getInvoices } from "@/services/invoices.service";
import { getProducts } from "@/services/products.service";
import { getQuotes } from "@/services/quotes.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Invoice, Quote } from "@/types/finance";
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

function formatLabel(value: string): string {
    return value
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
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

function buildLinkedQuoteValue(linkedQuote: Quote | null): ReactNode {
    if (!linkedQuote) {
        return "No linked quote yet";
    }

    return (
        <span>
            <Link
                href={`/finance/quotes/${linkedQuote.id}`}
                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
            >
                {linkedQuote.number}
            </Link>
            <span className="ml-2 text-slate-500">({linkedQuote.id})</span>
        </span>
    );
}

function getLoadErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Deal not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The deal could not be loaded from the backend.";
}

function getDeleteErrorMessage(error: unknown): string {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { status?: number; data?: { detail?: string } } }).response;
        if (response?.status === 404) {
            return "Deal not found.";
        }

        if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
            return response.data.detail;
        }
    }

    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Deal not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The deal could not be deleted.";
}

export default function DealDetailPage() {
    const auth = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const params = useParams<{ dealId: string }>();
    const rawDealId = params?.dealId;
    const dealId = Array.isArray(rawDealId) ? rawDealId[0] : rawDealId;
    const createdFrom = searchParams.get("createdFrom");

    const [deal, setDeal] = useState<Deal | null>(null);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [relatedQuotes, setRelatedQuotes] = useState<Quote[]>([]);
    const [relatedInvoices, setRelatedInvoices] = useState<Invoice[]>([]);
    const [isQuoteLookupLoading, setIsQuoteLookupLoading] = useState<boolean>(true);
    const [relatedFinanceMessage, setRelatedFinanceMessage] = useState<string>("");
    const [isDeleting, setIsDeleting] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [actionError, setActionError] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            setIsQuoteLookupLoading(false);
            return;
        }

        if (!dealId) {
            setErrorMessage("Invalid deal id.");
            setIsLoading(false);
            setIsQuoteLookupLoading(false);
            return;
        }

        let isMounted = true;

        async function loadDealDetail(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                setActionError("");
                setRelatedFinanceMessage("");
                setRelatedQuotes([]);
                setRelatedInvoices([]);
                setIsQuoteLookupLoading(true);

                const [dealResponse, companiesResponse, contactsResponse, productsResponse] =
                    await Promise.all([
                        getDealById(dealId),
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                    ]);

                let resolvedQuotes: Quote[] = [];
                let resolvedInvoices: Invoice[] = [];
                try {
                    const linkedQuotes = await getQuotes({
                        company_id: dealResponse.company_id,
                        limit: 20,
                        offset: 0,
                    });
                    resolvedQuotes = (linkedQuotes.items ?? []).filter((quote) => quote.deal_id === dealId);

                    const linkedInvoices = await getInvoices({
                        company_id: dealResponse.company_id,
                        limit: 50,
                        offset: 0,
                    });
                    const quoteIds = new Set(resolvedQuotes.map((quote) => quote.id));
                    resolvedInvoices = (linkedInvoices.items ?? []).filter((invoice) => {
                        const sourceQuoteId = "source_quote_id" in invoice ? invoice.source_quote_id : null;
                        return typeof sourceQuoteId === "string" && quoteIds.has(sourceQuoteId);
                    });
                } catch (error) {
                    console.warn("Linked finance lookup failed on deal detail:", error);
                    if (isMounted) {
                        setRelatedFinanceMessage(
                            "Related finance documents could not be fully loaded. You can still work from this deal.",
                        );
                    }
                }

                if (!isMounted) {
                    return;
                }

                setDeal(dealResponse);
                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setProducts(productsResponse.items ?? []);
                setRelatedQuotes(resolvedQuotes);
                setRelatedInvoices(resolvedInvoices);
            } catch (error) {
                console.error("Failed to load deal detail:", error);
                if (!isMounted) {
                    return;
                }
                setErrorMessage(getLoadErrorMessage(error));
                setDeal(null);
                setRelatedQuotes([]);
                setRelatedInvoices([]);
                setRelatedFinanceMessage("");
            } finally {
                if (isMounted) {
                    setIsQuoteLookupLoading(false);
                    setIsLoading(false);
                }
            }
        }

        void loadDealDetail();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, dealId]);

    async function handleDeleteDeal(): Promise<void> {
        if (!dealId || !deal) {
            return;
        }

        const confirmed = window.confirm(
            `Delete ${deal.name}? This removes the deal from the current tenant.`,
        );
        if (!confirmed) {
            return;
        }

        try {
            setIsDeleting(true);
            setActionError("");
            await deleteDeal(dealId);
            router.push("/deals");
            router.refresh();
        } catch (error) {
            console.error("Failed to delete deal:", error);
            setActionError(getDeleteErrorMessage(error));
        } finally {
            setIsDeleting(false);
        }
    }

    const latestQuote = relatedQuotes[0] ?? null;

    const detailRows = useMemo<Array<{ label: string; value: ReactNode }>>(() => {
        if (!deal) {
            return [];
        }

        return [
            { label: "Deal Name", value: deal.name },
            { label: "Stage", value: formatLabel(deal.stage) },
            { label: "Status", value: formatLabel(deal.status) },
            { label: "Amount", value: formatMoney(deal.amount, deal.currency) },
            { label: "Currency", value: deal.currency },
            { label: "Company", value: buildCompanyValue(companies, deal.company_id) },
            { label: "Contact", value: buildContactValue(contacts, deal.contact_id) },
            { label: "Product", value: buildProductValue(products, deal.product_id) },
            { label: "Latest Quote", value: buildLinkedQuoteValue(latestQuote) },
            { label: "Related Invoices", value: relatedInvoices.length === 0 ? "No linked invoices yet" : `${relatedInvoices.length} invoice${relatedInvoices.length === 1 ? "" : "s"}` },
            { label: "Next Follow-up", value: deal.next_follow_up_at ? formatDateTime(deal.next_follow_up_at) : "Not scheduled" },
            { label: "Follow-up Note", value: deal.follow_up_note?.trim() ? deal.follow_up_note : "No follow-up note" },
            { label: "Expected Close Date", value: deal.expected_close_date ? formatDate(deal.expected_close_date) : "Not set" },
            { label: "Notes", value: deal.notes?.trim() ? deal.notes : "No notes" },
            { label: "Created At", value: formatDateTime(deal.created_at) },
            { label: "Updated At", value: formatDateTime(deal.updated_at) },
        ];
    }, [companies, contacts, deal, latestQuote, products, relatedInvoices.length]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">
                            {deal ? deal.name : "Deal Details"}
                        </h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Read-only deal details.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {dealId ? (
                            <Link
                                href={`/deals/${dealId}/edit`}
                                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                            >
                                Edit Deal
                            </Link>
                        ) : null}
                        {isQuoteLookupLoading ? (
                            <button
                                type="button"
                                disabled
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 opacity-70"
                            >
                                Checking...
                            </button>
                        ) : latestQuote ? (
                            <Link
                                href={`/finance/quotes/${latestQuote.id}`}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                            >
                                View Quote ({latestQuote.number})
                            </Link>
                        ) : (
                            <Link
                                href={deal ? `/finance/quotes/create?deal_id=${deal.id}` : "/finance/quotes/create"}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                            >
                                Create Quote
                            </Link>
                        )}
                        <button
                            type="button"
                            onClick={() => {
                                void handleDeleteDeal();
                            }}
                            disabled={!deal || isDeleting}
                            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isDeleting ? "Deleting..." : "Delete Deal"}
                        </button>
                        <Link
                            href="/deals"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all deals
                        </Link>
                    </div>
                </div>

                {createdFrom === "lead-intake" ? (
                    <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4">
                        <p className="text-sm text-green-700">
                            Lead created successfully and added to the deal flow.
                        </p>
                    </div>
                ) : null}

                {actionError ? (
                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
                        <p className="text-sm text-red-700">{actionError}</p>
                    </div>
                ) : null}
                {relatedFinanceMessage ? (
                    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
                        <p className="text-sm text-amber-800">{relatedFinanceMessage}</p>
                    </div>
                ) : null}
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Loading deal details
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching deal, company, contact, product, and linked quote data from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">
                        Failed to load deal
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !deal ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Deal unavailable
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested deal could not be found.
                    </p>
                </section>
            ) : (
                <>
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

                    <DealFollowUpCard
                        deal={deal}
                        onUpdated={(updatedDeal) => {
                            setDeal((currentDeal) => ({
                                ...(currentDeal ?? updatedDeal),
                                ...updatedDeal,
                            }));
                        }}
                    />

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Related quotes</h2>
                        <p className="mt-2 text-sm text-slate-600">
                            Quotes created from this deal stay linked through the existing commercial flow.
                        </p>

                        {relatedQuotes.length === 0 ? (
                            <p className="mt-4 text-sm text-slate-600">
                                No quotes have been created from this deal yet.
                            </p>
                        ) : (
                            <div className="mt-4 space-y-3">
                                {relatedQuotes.map((quote) => (
                                    <div
                                        key={quote.id}
                                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-4"
                                    >
                                        <div>
                                            <Link
                                                href={`/finance/quotes/${quote.id}`}
                                                className="text-sm font-semibold text-slate-900 underline underline-offset-2"
                                            >
                                                {quote.number}
                                            </Link>
                                            <p className="mt-1 text-sm text-slate-600">
                                                {formatMoney(quote.total_amount, quote.currency)} • {formatLabel(quote.status)}
                                            </p>
                                        </div>
                                        <Link
                                            href={`/finance/quotes/${quote.id}`}
                                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                        >
                                            Open quote
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Related invoices</h2>
                        <p className="mt-2 text-sm text-slate-600">
                            Invoices are derived from accepted quotes and surfaced here when they can be resolved from linked quotes.
                        </p>

                        {relatedInvoices.length === 0 ? (
                            <p className="mt-4 text-sm text-slate-600">
                                Related invoices are not wired yet in the live API.
                            </p>
                        ) : (
                            <div className="mt-4 space-y-3">
                                {relatedInvoices.map((invoice) => (
                                    <div
                                        key={invoice.id}
                                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-4"
                                    >
                                        <div>
                                            <Link
                                                href={`/finance/invoices/${invoice.id}`}
                                                className="text-sm font-semibold text-slate-900 underline underline-offset-2"
                                            >
                                                {invoice.number}
                                            </Link>
                                            <p className="mt-1 text-sm text-slate-600">
                                                {formatMoney(invoice.total_amount, invoice.currency)} • {formatLabel(invoice.status)}
                                            </p>
                                        </div>
                                        <Link
                                            href={`/finance/invoices/${invoice.id}`}
                                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                        >
                                            Open invoice
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

"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import InvoicePaymentsCard from "@/components/finance/InvoicePaymentsCard";
import { useAuth } from "@/hooks/use-auth";
import {
    getMissingSecondaryCurrencyRateMessage,
    getSecondaryCurrencyDisplay,
} from "@/lib/finance-currency";
import { getJournalEntries } from "@/services/accounting.service";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDealById } from "@/services/deals.service";
import { deleteInvoice, getInvoiceById } from "@/services/invoices.service";
import { getProducts } from "@/services/products.service";
import { getQuoteById } from "@/services/quotes.service";
import { getCurrentTenant } from "@/services/tenants.service";
import type { JournalEntry } from "@/types/accounting";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Invoice, Quote } from "@/types/finance";
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
            return "Invoice not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The invoice could not be loaded from the backend.";
}

function getDeleteErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Invoice not found. It may have already been deleted.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The invoice could not be deleted.";
}

function getCompanyName(companies: Company[], companyId: string): string {
    return companies.find((company) => company.id === companyId)?.name ?? companyId;
}

function buildCompanyValue(companies: Company[], companyId: string): ReactNode {
    return (
        <Link
            href={`/companies/${companyId}`}
            className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
        >
            {getCompanyName(companies, companyId)}
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

export default function InvoiceDetailPage() {
    const auth = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const params = useParams<{ invoiceId: string }>();
    const rawInvoiceId = params?.invoiceId;
    const invoiceId = Array.isArray(rawInvoiceId) ? rawInvoiceId[0] : rawInvoiceId;

    const [invoice, setInvoice] = useState<Invoice | null>(null);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [tenant, setTenant] = useState<Tenant | null>(null);
    const [sourceQuote, setSourceQuote] = useState<Quote | null>(null);
    const [sourceDeal, setSourceDeal] = useState<Deal | null>(null);
    const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState<boolean>(false);
    const [isDeleting, setIsDeleting] = useState<boolean>(false);
    const [deleteError, setDeleteError] = useState<string>("");

    const loadInvoiceDetail = useCallback(async (): Promise<void> => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        if (!invoiceId) {
            setErrorMessage("Invalid invoice id.");
            setIsLoading(false);
            return;
        }

        try {
            setIsLoading(true);
            setErrorMessage("");

            const [invoiceResponse, companiesResponse, contactsResponse, productsResponse, tenantResponse] =
                await Promise.all([
                    getInvoiceById(invoiceId),
                    getCompanies(),
                    getContacts(),
                    getProducts(),
                    getCurrentTenant(),
                ]);

            const journalEntriesResponse = await getJournalEntries({
                source_type: "invoice",
                source_id: invoiceResponse.id,
                limit: 20,
                offset: 0,
            });

            let resolvedSourceQuote: Quote | null = null;
            let resolvedSourceDeal: Deal | null = null;
            if (invoiceResponse.source_quote_id) {
                try {
                    resolvedSourceQuote = await getQuoteById(invoiceResponse.source_quote_id);
                    const dealId = resolvedSourceQuote.source_deal_id ?? resolvedSourceQuote.deal_id;
                    if (dealId) {
                        resolvedSourceDeal = await getDealById(dealId);
                    }
                } catch (error) {
                    console.warn("Source quote or deal could not be loaded for invoice detail:", error);
                }
            }

            setInvoice(invoiceResponse);
            setCompanies(companiesResponse.items ?? []);
            setContacts(contactsResponse.items ?? []);
            setProducts(productsResponse.items ?? []);
            setTenant(tenantResponse);
            setSourceQuote(resolvedSourceQuote);
            setSourceDeal(resolvedSourceDeal);
            setJournalEntries(journalEntriesResponse.items ?? []);
        } catch (error) {
            console.error("Failed to load invoice detail:", error);
            setErrorMessage(getLoadErrorMessage(error));
            setInvoice(null);
            setTenant(null);
            setSourceQuote(null);
            setSourceDeal(null);
            setJournalEntries([]);
        } finally {
            setIsLoading(false);
        }
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, invoiceId]);

    useEffect(() => {
        void loadInvoiceDetail();
    }, [loadInvoiceDetail]);

    async function handleDeleteConfirmed(): Promise<void> {
        if (!invoiceId || isDeleting) {
            return;
        }

        try {
            setDeleteError("");
            setIsDeleting(true);

            await deleteInvoice(invoiceId);

            router.push("/finance/invoices");
            router.refresh();
        } catch (error) {
            console.error("Failed to delete invoice:", error);
            setDeleteError(getDeleteErrorMessage(error));
        } finally {
            setIsDeleting(false);
        }
    }

    const detailRows = useMemo(() => {
        if (!invoice) {
            return [];
        }

        const sourceQuoteValue: ReactNode = sourceQuote ? (
            <Link
                href={`/finance/quotes/${sourceQuote.id}`}
                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
            >
                {sourceQuote.number}
            </Link>
        ) : invoice.source_quote_id ? (
            <Link
                href={`/finance/quotes/${invoice.source_quote_id}`}
                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
            >
                {invoice.source_quote_id}
            </Link>
        ) : (
            "Not converted from a quote"
        );

        const sourceDealValue: ReactNode = sourceDeal ? (
            <Link
                href={`/deals/${sourceDeal.id}`}
                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
            >
                {sourceDeal.name}
            </Link>
        ) : sourceQuote?.source_deal_id || sourceQuote?.deal_id ? (
            <Link
                href={`/deals/${sourceQuote?.source_deal_id ?? sourceQuote?.deal_id}`}
                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
            >
                {sourceQuote?.source_deal_id ?? sourceQuote?.deal_id}
            </Link>
        ) : (
            "No related deal"
        );

        return [
            { label: "Invoice Number", value: invoice.number },
            { label: "Company", value: buildCompanyValue(companies, invoice.company_id) },
            { label: "Contact", value: buildContactValue(contacts, invoice.contact_id) },
            { label: "Product", value: buildProductValue(products, invoice.product_id) },
            { label: "Source Quote", value: sourceQuoteValue },
            { label: "Source Deal", value: sourceDealValue },
            { label: "Issue Date", value: formatDate(invoice.issue_date) },
            { label: "Due Date", value: formatDate(invoice.due_date) },
            { label: "Currency", value: invoice.currency },
            { label: "Total Amount", value: formatMoney(invoice.total_amount, invoice.currency) },
            { label: "Status", value: formatStatus(invoice.status) },
            { label: "Notes", value: invoice.notes?.trim() ? invoice.notes : "No notes" },
            { label: "Created At", value: formatDateTime(invoice.created_at) },
            { label: "Updated At", value: formatDateTime(invoice.updated_at) },
        ];
    }, [companies, contacts, invoice, products, sourceDeal, sourceQuote]);

    const createdFromQuote = searchParams.get("createdFrom") === "quote";
    const convertedAmount = invoice
        ? getSecondaryCurrencyDisplay(tenant, invoice.total_amount, invoice.currency)
        : null;
    const missingRateMessage = invoice
        ? getMissingSecondaryCurrencyRateMessage(tenant, invoice.currency)
        : null;

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">
                            {invoice ? invoice.number : "Invoice Details"}
                        </h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Read-only invoice details.
                        </p>
                        {createdFromQuote ? (
                            <p className="mt-2 text-sm text-emerald-700">
                                Invoice created successfully from the quote context and added to the commercial flow.
                            </p>
                        ) : null}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        <Link
                            href={
                                invoiceId
                                    ? `/finance/invoices/${invoiceId}/edit`
                                    : "/finance/invoices"
                            }
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Edit invoice
                        </Link>
                        <Link
                            href="/finance/invoices"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all invoices
                        </Link>
                        {invoice ? (
                            <button
                                type="button"
                                onClick={() => {
                                    setDeleteError("");
                                    setIsDeleteConfirmOpen(true);
                                }}
                                disabled={isDeleting}
                                className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                {isDeleting ? "Deleting..." : "Delete invoice"}
                            </button>
                        ) : null}
                    </div>
                </div>

                {isDeleteConfirmOpen && invoice ? (
                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
                        <p className="text-sm font-medium text-red-800">
                            Are you sure you want to delete {invoice.number}?
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
                                {isDeleting ? "Deleting..." : "Yes, delete invoice"}
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
                        Loading invoice details
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching invoice, company, contact, and product data from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">
                        Failed to load invoice
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !invoice ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Invoice unavailable
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested invoice could not be found.
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

                    <InvoicePaymentsCard invoice={invoice} onPaymentRecorded={loadInvoiceDetail} />

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h2 className="text-xl font-semibold text-slate-900">Accounting visibility</h2>
                                <p className="mt-2 text-sm text-slate-600">
                                    Invoice accounting stays grounded in posted journal entries from supported invoice events only.
                                </p>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <Link
                                    href={`/finance/accounting?source_type=invoice&source_id=${invoice.id}`}
                                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                >
                                    View accounting entries
                                </Link>
                                <Link
                                    href="/reports/finance"
                                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                >
                                    Open finance reports
                                </Link>
                            </div>
                        </div>

                        {invoice.status === "draft" ? (
                            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                                <p className="text-sm font-medium text-slate-900">No accounting entry has been posted yet.</p>
                                <p className="mt-2 text-sm text-slate-600">
                                    Draft invoices remain outside accounting until they are issued.
                                </p>
                            </div>
                        ) : journalEntries.length === 0 ? (
                            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
                                <p className="text-sm font-medium text-amber-900">No journal entries are visible yet for this invoice.</p>
                                <p className="mt-2 text-sm text-amber-800">
                                    This usually means the invoice has not reached a posting state in the current environment yet.
                                </p>
                            </div>
                        ) : (
                            <div className="mt-6 space-y-3">
                                {journalEntries.map((entry) => (
                                    <div key={entry.id} className="rounded-lg border border-slate-200 px-4 py-4">
                                        <div className="flex flex-wrap items-start justify-between gap-4">
                                            <div>
                                                <p className="font-medium text-slate-900">{entry.memo}</p>
                                                <p className="mt-1 text-sm text-slate-600">
                                                    {formatDate(entry.entry_date)} · {entry.source_event
                                                        ? formatStatus(entry.source_event.replaceAll("_", " "))
                                                        : "Posted journal entry"}
                                                </p>
                                            </div>
                                            <p className="text-sm font-medium text-slate-900">
                                                {formatMoney(entry.total_debit, entry.currency)}
                                            </p>
                                        </div>
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

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { formatDealLabel, getDealFollowUpLabel, getDealFollowUpState } from "@/lib/deals";
import { getInvoices } from "@/services/invoices.service";
import { convertDealToQuote, getQuotes } from "@/services/quotes.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Invoice, Quote } from "@/types/finance";
import type { Product } from "@/types/product";

type DealsListProps = {
    deals: Deal[];
    total: number;
    companies: Company[];
    contacts: Contact[];
    products: Product[];
    title?: string;
    description?: string;
};

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

function getCompanyName(companies: Company[], companyId: string): string {
    return companies.find((company) => company.id === companyId)?.name ?? companyId;
}

function getContactName(contacts: Contact[], contactId: string | null): string {
    if (!contactId) {
        return "";
    }

    const contact = contacts.find((item) => item.id === contactId);
    if (!contact) {
        return contactId;
    }

    return `${contact.first_name} ${contact.last_name ?? ""}`.trim();
}

function getProductName(products: Product[], productId: string | null): string {
    if (!productId) {
        return "";
    }

    const product = products.find((item) => item.id === productId);
    if (!product) {
        return productId;
    }

    return product.name;
}

function buildProductValue(products: Product[], productId: string | null): ReactNode {
    if (!productId) {
        return "";
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

function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

function getFollowUpToneClasses(state: ReturnType<typeof getDealFollowUpState>): string {
    if (state === "overdue") {
        return "bg-red-100 text-red-700";
    }
    if (state === "due-today") {
        return "bg-amber-100 text-amber-700";
    }
    if (state === "upcoming") {
        return "bg-blue-100 text-blue-700";
    }
    return "bg-slate-100 text-slate-600";
}

export default function DealsList({
    deals,
    total,
    companies,
    contacts,
    products,
    title = "Deals",
    description = "Loaded from the backend API.",
}: DealsListProps) {
    const router = useRouter();
    const convertLockRef = useRef<Set<string>>(new Set());
    const [convertingByDealId, setConvertingByDealId] = useState<Record<string, boolean>>({});
    const [conversionErrorByDealId, setConversionErrorByDealId] = useState<Record<string, string>>({});
    const [linkedQuoteIdByDealId, setLinkedQuoteIdByDealId] = useState<Record<string, string>>({});
    const [linkedQuoteByDealId, setLinkedQuoteByDealId] = useState<Record<string, Quote>>({});
    const [linkedInvoiceByDealId, setLinkedInvoiceByDealId] = useState<Record<string, Invoice>>({});
    const [lookupLoadingByDealId, setLookupLoadingByDealId] = useState<Record<string, boolean>>({});

    useEffect(() => {
        if (deals.length === 0) {
            setLinkedQuoteIdByDealId({});
            setLinkedQuoteByDealId({});
            setLinkedInvoiceByDealId({});
            setLookupLoadingByDealId({});
            return;
        }

        let isMounted = true;
        const uniqueDealIds = Array.from(new Set(deals.map((deal) => deal.id)));

        setLookupLoadingByDealId(
            Object.fromEntries(uniqueDealIds.map((dealId) => [dealId, true])),
        );

        async function loadLinkedQuotes(): Promise<void> {
            const lookupResults = await Promise.all(
                uniqueDealIds.map(async (dealId) => {
                    try {
                        const quoteResponse = await getQuotes({
                            source_deal_id: dealId,
                            limit: 1,
                            offset: 0,
                        });
                        const quote = quoteResponse.items?.[0] ?? null;
                        if (!quote) {
                            return {
                                dealId,
                                quote: null,
                                invoice: null,
                            };
                        }

                        const invoiceResponse = await getInvoices({
                            source_quote_id: quote.id,
                            limit: 1,
                            offset: 0,
                        });
                        return {
                            dealId,
                            quote,
                            invoice: invoiceResponse.items?.[0] ?? null,
                        };
                    } catch (error) {
                        console.warn("Failed to lookup linked commercial records for deal:", dealId, error);
                        return {
                            dealId,
                            quote: null,
                            invoice: null,
                        };
                    }
                }),
            );

            if (!isMounted) {
                return;
            }

            const nextLinkedByDealId: Record<string, string> = {};
            const nextLinkedQuoteByDealId: Record<string, Quote> = {};
            const nextLinkedInvoiceByDealId: Record<string, Invoice> = {};
            const nextLookupLoadingByDealId: Record<string, boolean> = {};

            lookupResults.forEach(({ dealId, quote, invoice }) => {
                if (quote) {
                    nextLinkedByDealId[dealId] = quote.id;
                    nextLinkedQuoteByDealId[dealId] = quote;
                }
                if (invoice) {
                    nextLinkedInvoiceByDealId[dealId] = invoice;
                }
                nextLookupLoadingByDealId[dealId] = false;
            });

            setLinkedQuoteIdByDealId(nextLinkedByDealId);
            setLinkedQuoteByDealId(nextLinkedQuoteByDealId);
            setLinkedInvoiceByDealId(nextLinkedInvoiceByDealId);
            setLookupLoadingByDealId(nextLookupLoadingByDealId);
        }

        void loadLinkedQuotes();

        return () => {
            isMounted = false;
        };
    }, [deals]);

    async function handleConvertToQuote(deal: Deal): Promise<void> {
        if (
            convertLockRef.current.has(deal.id)
            || Boolean(lookupLoadingByDealId[deal.id])
            || Boolean(linkedQuoteIdByDealId[deal.id])
        ) {
            return;
        }

        try {
            convertLockRef.current.add(deal.id);
            setConvertingByDealId((current) => ({
                ...current,
                [deal.id]: true,
            }));
            setConversionErrorByDealId((current) => ({
                ...current,
                [deal.id]: "",
            }));

            const quote = await convertDealToQuote(deal.id);
            setLinkedQuoteIdByDealId((current) => ({
                ...current,
                [deal.id]: quote.id,
            }));

            router.push(`/finance/quotes/${quote.id}`);
            router.refresh();
        } catch (error: unknown) {
            console.error("Failed to convert deal to quote:", error);

            let message = "The deal could not be converted to a quote.";
            if (
                typeof error === "object" &&
                error !== null &&
                "response" in error
            ) {
                const response = (error as {
                    response?: { data?: { detail?: string } };
                }).response;

                if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
                    message = response.data.detail;
                }
            }

            setConversionErrorByDealId((current) => ({
                ...current,
                [deal.id]: message,
            }));
        } finally {
            convertLockRef.current.delete(deal.id);
            setConvertingByDealId((current) => ({
                ...current,
                [deal.id]: false,
            }));
        }
    }

    if (deals.length === 0) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h2 className="text-2xl font-semibold text-slate-900">{title}</h2>
                <p className="mt-2 text-sm text-slate-600">
                    Your tenant does not have any deals yet.
                </p>
            </section>
        );
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">{title}</h2>
            <p className="mt-2 text-sm text-slate-600">
                {total} deal{total === 1 ? "" : "s"} {description}
            </p>

            <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
                <table className="min-w-full border-collapse">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Name
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Company
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Contact
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Product
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Amount
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Stage
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Status
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Expected Close
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Follow-up
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Commercial
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {deals.map((deal) => (
                            <tr key={deal.id} className="hover:bg-slate-50">
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-900">
                                    <Link
                                        href={`/deals/${deal.id}`}
                                        className="font-medium text-slate-900 underline-offset-2 hover:underline"
                                    >
                                        {deal.name}
                                    </Link>
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {getCompanyName(companies, deal.company_id)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {getContactName(contacts, deal.contact_id)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {buildProductValue(products, deal.product_id)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {formatMoney(deal.amount, deal.currency)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {formatDealLabel(deal.stage)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {formatDealLabel(deal.status)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {deal.expected_close_date ?? ""}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    <div className="space-y-1">
                                        <span
                                            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${getFollowUpToneClasses(getDealFollowUpState(deal))}`}
                                        >
                                            {getDealFollowUpLabel(deal)}
                                        </span>
                                        <p className="text-xs text-slate-500">
                                            {deal.next_follow_up_at ? formatDateTime(deal.next_follow_up_at) : "No follow-up scheduled"}
                                        </p>
                                    </div>
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {lookupLoadingByDealId[deal.id] ? (
                                        <span className="text-xs text-slate-500">Checking...</span>
                                    ) : linkedInvoiceByDealId[deal.id] ? (
                                        <div className="space-y-1">
                                            <Link
                                                href={`/finance/invoices/${linkedInvoiceByDealId[deal.id].id}`}
                                                className="inline-flex rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700 transition hover:bg-green-200"
                                            >
                                                Invoice {linkedInvoiceByDealId[deal.id].number}
                                            </Link>
                                            <p className="text-xs text-slate-500">
                                                From quote {linkedQuoteByDealId[deal.id]?.number}
                                            </p>
                                        </div>
                                    ) : linkedQuoteByDealId[deal.id] ? (
                                        <div className="space-y-1">
                                            <Link
                                                href={`/finance/quotes/${linkedQuoteByDealId[deal.id].id}`}
                                                className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-200"
                                            >
                                                Quote {linkedQuoteByDealId[deal.id].number}
                                            </Link>
                                            <p className="text-xs text-slate-500">
                                                No invoice linked yet
                                            </p>
                                        </div>
                                    ) : (
                                        <span className="text-xs text-slate-500">No quote yet</span>
                                    )}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {linkedQuoteIdByDealId[deal.id] ? (
                                        <Link
                                            href={`/finance/quotes/${linkedQuoteIdByDealId[deal.id]}`}
                                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-100"
                                        >
                                            View Quote
                                        </Link>
                                    ) : (
                                        <button
                                            type="button"
                                            onClick={() => {
                                                void handleConvertToQuote(deal);
                                            }}
                                            disabled={Boolean(lookupLoadingByDealId[deal.id]) || Boolean(convertingByDealId[deal.id])}
                                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {lookupLoadingByDealId[deal.id]
                                                ? "Checking..."
                                                : convertingByDealId[deal.id]
                                                    ? "Creating quote..."
                                                    : "Create Quote"}
                                        </button>
                                    )}
                                    {conversionErrorByDealId[deal.id] ? (
                                        <p className="mt-2 text-xs text-red-600">{conversionErrorByDealId[deal.id]}</p>
                                    ) : null}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

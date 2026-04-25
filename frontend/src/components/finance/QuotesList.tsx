"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { updateQuoteStatus } from "@/services/quotes.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Quote, QuoteStatus } from "@/types/finance";
import type { Product } from "@/types/product";

type QuotesListProps = {
    quotes: Quote[];
    total: number;
    companies: Company[];
    contacts: Contact[];
    deals: Deal[];
    products: Product[];
    onStatusUpdated?: () => Promise<void> | void;
};

const NEXT_STATUS_OPTIONS: Record<QuoteStatus, QuoteStatus[]> = {
    draft: ["sent", "rejected"],
    sent: ["accepted", "rejected", "expired"],
    accepted: [],
    rejected: [],
    expired: [],
};

function formatStatus(status: string): string {
    return status
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

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

function getDealName(deals: Deal[], dealId: string | null): string {
    if (!dealId) {
        return "";
    }

    const deal = deals.find((item) => item.id === dealId);
    if (!deal) {
        return dealId;
    }

    return deal.name;
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

function getErrorMessage(error: unknown): string {
    if (
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof error.response === "object" &&
        error.response !== null &&
        "data" in error.response &&
        typeof error.response.data === "object" &&
        error.response.data !== null &&
        "detail" in error.response.data &&
        typeof error.response.data.detail === "string"
    ) {
        return error.response.data.detail;
    }

    if (error instanceof Error) {
        return error.message;
    }

    return "Failed to update quote status.";
}

export default function QuotesList({
    quotes,
    total,
    companies,
    contacts,
    deals,
    products,
    onStatusUpdated,
}: QuotesListProps) {
    const [quoteRows, setQuoteRows] = useState<Quote[]>(quotes);
    const [updatingQuoteId, setUpdatingQuoteId] = useState<string | null>(null);
    const [errorByQuoteId, setErrorByQuoteId] = useState<Record<string, string>>({});

    useEffect(() => {
        setQuoteRows(quotes);
        setErrorByQuoteId({});
    }, [quotes]);

    async function handleStatusChange(
        quoteId: string,
        nextStatus: QuoteStatus,
    ): Promise<void> {
        try {
            setUpdatingQuoteId(quoteId);
            setErrorByQuoteId((current) => ({
                ...current,
                [quoteId]: "",
            }));

            const updatedQuote = await updateQuoteStatus(quoteId, nextStatus);

            setQuoteRows((current) =>
                current.map((quote) =>
                    quote.id === quoteId ? updatedQuote : quote,
                ),
            );

            if (onStatusUpdated) {
                await onStatusUpdated();
            }
        } catch (error) {
            setErrorByQuoteId((current) => ({
                ...current,
                [quoteId]: getErrorMessage(error),
            }));
        } finally {
            setUpdatingQuoteId(null);
        }
    }

    if (quoteRows.length === 0) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h2 className="text-2xl font-semibold text-slate-900">Quotes</h2>
                <p className="mt-2 text-sm text-slate-600">
                    No quotes available yet.
                </p>
            </section>
        );
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Quotes</h2>
            <p className="mt-2 text-sm text-slate-600">
                {total} quote{total === 1 ? "" : "s"} loaded from the backend API.
            </p>

            <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
                <table className="min-w-full border-collapse">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Number
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Company
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Contact
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Deal
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Product
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Amount
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Status
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Expiry Date
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {quoteRows.map((quote) => {
                            const nextActions = NEXT_STATUS_OPTIONS[quote.status];
                            const isUpdating = updatingQuoteId === quote.id;
                            const errorMessage = errorByQuoteId[quote.id];

                            return (
                                <tr key={quote.id} className="align-top hover:bg-slate-50">
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-900">
                                        <Link
                                            href={`/finance/quotes/${quote.id}`}
                                            className="font-medium text-slate-900 underline-offset-2 hover:underline"
                                        >
                                            {quote.number}
                                        </Link>
                                        {quote.source_deal_id ? (
                                            <p className="mt-1 text-xs text-slate-500">
                                                From deal: {getDealName(deals, quote.source_deal_id)}
                                            </p>
                                        ) : null}
                                    </td>
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                        {getCompanyName(companies, quote.company_id)}
                                    </td>
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                        {getContactName(contacts, quote.contact_id)}
                                    </td>
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                        {getDealName(deals, quote.deal_id)}
                                    </td>
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                        {getProductName(products, quote.product_id)}
                                    </td>
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                        {formatMoney(quote.total_amount, quote.currency)}
                                    </td>
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                        {formatStatus(quote.status)}
                                    </td>
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                        {quote.expiry_date}
                                    </td>
                                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                        {nextActions.length === 0 ? (
                                            <span className="text-slate-400">No actions</span>
                                        ) : (
                                            <div className="flex flex-wrap gap-2">
                                                {nextActions.map((nextStatus) => (
                                                    <button
                                                        key={nextStatus}
                                                        type="button"
                                                        onClick={() =>
                                                            void handleStatusChange(quote.id, nextStatus)
                                                        }
                                                        disabled={isUpdating}
                                                        className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                                    >
                                                        {isUpdating
                                                            ? "Updating..."
                                                            : `Mark ${formatStatus(nextStatus)}`}
                                                    </button>
                                                ))}
                                            </div>
                                        )}

                                        {errorMessage ? (
                                            <p className="mt-2 text-xs text-red-600">{errorMessage}</p>
                                        ) : null}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

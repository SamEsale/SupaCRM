"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { updateInvoiceStatus } from "@/services/invoices.service";
import type { Invoice, InvoiceStatus } from "@/types/finance";
import type { Company, Contact } from "@/types/crm";
import type { Product } from "@/types/product";

type InvoicesListProps = {
    invoices: Invoice[];
    total: number;
    companies: Company[];
    contacts: Contact[];
    products: Product[];
    onStatusUpdated?: () => Promise<void> | void;
};

const NEXT_STATUS_OPTIONS: Record<InvoiceStatus, InvoiceStatus[]> = {
    draft: ["issued", "cancelled"],
    issued: ["paid", "overdue", "cancelled"],
    paid: [],
    overdue: ["paid", "cancelled"],
    cancelled: [],
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
    return companies.find((c) => c.id === companyId)?.name ?? companyId;
}

function getContactName(contacts: Contact[], contactId: string | null): string {
    if (!contactId) return "";

    const contact = contacts.find((c) => c.id === contactId);
    if (!contact) return contactId;

    return `${contact.first_name} ${contact.last_name ?? ""}`.trim();
}

function getProductName(products: Product[], productId: string | null): string {
    if (!productId) return "";

    const product = products.find((p) => p.id === productId);
    if (!product) return productId;

    return product.name;
}

function formatStatus(status: string): string {
    return status
        .split(" ")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
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
        "detail" in error.response &&
        typeof error.response.detail === "string"
    ) {
        return error.response.detail;
    }

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

    return "Failed to update invoice status.";
}

export default function InvoicesList({
    invoices,
    total,
    companies,
    contacts,
    products,
    onStatusUpdated,
}: InvoicesListProps) {
    const [invoiceRows, setInvoiceRows] = useState<Invoice[]>(invoices);
    const [updatingInvoiceId, setUpdatingInvoiceId] = useState<string | null>(null);
    const [errorByInvoiceId, setErrorByInvoiceId] = useState<Record<string, string>>(
        {},
    );

    useEffect(() => {
        setInvoiceRows(invoices);
        setErrorByInvoiceId({});
    }, [invoices]);

    async function handleStatusChange(
        invoiceId: string,
        nextStatus: InvoiceStatus,
    ): Promise<void> {
        try {
            setUpdatingInvoiceId(invoiceId);
            setErrorByInvoiceId((current) => ({
                ...current,
                [invoiceId]: "",
            }));

            const updatedInvoice = await updateInvoiceStatus(invoiceId, nextStatus);

            setInvoiceRows((current) =>
                current.map((invoice) =>
                    invoice.id === invoiceId ? updatedInvoice : invoice,
                ),
            );

            if (onStatusUpdated) {
                await onStatusUpdated();
            }
        } catch (error) {
            setErrorByInvoiceId((current) => ({
                ...current,
                [invoiceId]: getErrorMessage(error),
            }));
        } finally {
            setUpdatingInvoiceId(null);
        }
    }

    if (invoiceRows.length === 0) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h2 className="text-2xl font-semibold text-slate-900">Invoices</h2>
                <p className="mt-2 text-sm text-slate-600">
                    No invoices available yet.
                </p>
            </section>
        );
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Invoices</h2>
            <p className="mt-2 text-sm text-slate-600">
                {total} invoices loaded from the backend API.
            </p>

            <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
                <table className="min-w-full border-collapse">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Number</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Company</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Contact</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Product</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Amount</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Status</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Due Date</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {invoiceRows.map((invoice) => {
                            const nextActions = NEXT_STATUS_OPTIONS[invoice.status];
                            const isUpdating = updatingInvoiceId === invoice.id;
                            const errorMessage = errorByInvoiceId[invoice.id];

                            return (
                                <tr key={invoice.id} className="align-top hover:bg-slate-50">
                                    <td className="px-4 py-3 text-sm">
                                        <Link
                                            href={`/finance/invoices/${invoice.id}`}
                                            className="font-medium text-slate-900 underline-offset-2 hover:underline"
                                        >
                                            {invoice.number}
                                        </Link>
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        {getCompanyName(companies, invoice.company_id)}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        {getContactName(contacts, invoice.contact_id)}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        {getProductName(products, invoice.product_id)}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        {formatMoney(invoice.total_amount, invoice.currency)}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        {formatStatus(invoice.status)}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        {invoice.due_date}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        {nextActions.length === 0 ? (
                                            <span className="text-slate-400">No actions</span>
                                        ) : (
                                            <div className="flex flex-wrap gap-2">
                                                {nextActions.map((nextStatus) => (
                                                    <button
                                                        key={nextStatus}
                                                        type="button"
                                                        onClick={() =>
                                                            handleStatusChange(
                                                                invoice.id,
                                                                nextStatus,
                                                            )
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
                                            <p className="mt-2 text-xs text-red-600">
                                                {errorMessage}
                                            </p>
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

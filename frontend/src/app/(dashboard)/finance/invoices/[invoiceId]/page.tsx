"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { deleteInvoice, getInvoiceById } from "@/services/invoices.service";
import { getProducts } from "@/services/products.service";
import type { Company, Contact } from "@/types/crm";
import type { Invoice } from "@/types/finance";
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

export default function InvoiceDetailPage() {
    const auth = useAuth();
    const router = useRouter();
    const params = useParams<{ invoiceId: string }>();
    const rawInvoiceId = params?.invoiceId;
    const invoiceId = Array.isArray(rawInvoiceId) ? rawInvoiceId[0] : rawInvoiceId;

    const [invoice, setInvoice] = useState<Invoice | null>(null);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState<boolean>(false);
    const [isDeleting, setIsDeleting] = useState<boolean>(false);
    const [deleteError, setDeleteError] = useState<string>("");

    useEffect(() => {
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

        let isMounted = true;

        async function loadInvoiceDetail(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const [invoiceResponse, companiesResponse, contactsResponse, productsResponse] =
                    await Promise.all([
                        getInvoiceById(invoiceId),
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                    ]);

                if (!isMounted) {
                    return;
                }

                setInvoice(invoiceResponse);
                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setProducts(productsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load invoice detail:", error);

                if (!isMounted) {
                    return;
                }

                setErrorMessage(getLoadErrorMessage(error));
                setInvoice(null);
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadInvoiceDetail();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, invoiceId]);

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

        return [
            { label: "Invoice Number", value: invoice.number },
            { label: "Company", value: getCompanyName(companies, invoice.company_id) },
            { label: "Contact", value: getContactName(contacts, invoice.contact_id) },
            { label: "Product", value: getProductName(products, invoice.product_id) },
            { label: "Issue Date", value: formatDate(invoice.issue_date) },
            { label: "Due Date", value: formatDate(invoice.due_date) },
            { label: "Currency", value: invoice.currency },
            { label: "Total Amount", value: formatMoney(invoice.total_amount, invoice.currency) },
            { label: "Status", value: formatStatus(invoice.status) },
            { label: "Notes", value: invoice.notes?.trim() ? invoice.notes : "No notes" },
            { label: "Created At", value: formatDateTime(invoice.created_at) },
            { label: "Updated At", value: formatDateTime(invoice.updated_at) },
        ];
    }, [companies, contacts, invoice, products]);

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

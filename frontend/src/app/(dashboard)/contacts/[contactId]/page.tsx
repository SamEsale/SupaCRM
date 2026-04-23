"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { buildLeadCreateHref, formatDealLabel } from "@/lib/deals";
import { getCompanyById } from "@/services/companies.service";
import { deleteContact, getContactById } from "@/services/contacts.service";
import { getDeals } from "@/services/deals.service";
import type { Company, Contact, Deal } from "@/types/crm";

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

function formatContactName(contact: Contact): string {
    return [contact.first_name, contact.last_name].filter(Boolean).join(" ") || contact.id;
}

function getLoadErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Contact not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The contact could not be loaded from the backend.";
}

function getActionErrorMessage(error: unknown, fallbackMessage: string): string {
    if (
        axios.isAxiosError(error) &&
        typeof error.response?.data?.detail === "string" &&
        error.response.data.detail.trim().length > 0
    ) {
        return error.response.data.detail;
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return fallbackMessage;
}

export default function ContactDetailPage() {
    const auth = useAuth();
    const router = useRouter();
    const params = useParams<{ contactId: string }>();
    const rawContactId = params?.contactId;
    const contactId = Array.isArray(rawContactId) ? rawContactId[0] : rawContactId;

    const [contact, setContact] = useState<Contact | null>(null);
    const [company, setCompany] = useState<Company | null>(null);
    const [relatedDeals, setRelatedDeals] = useState<Deal[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [relatedWarning, setRelatedWarning] = useState<string>("");
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

        if (!contactId) {
            setErrorMessage("Invalid contact id.");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadContactDetail(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                setRelatedWarning("");
                setRelatedDeals([]);
                setCompany(null);

                const contactResponse = await getContactById(contactId);

                const [companyResult, dealsResult] = await Promise.allSettled([
                    contactResponse.company_id
                        ? getCompanyById(contactResponse.company_id)
                        : Promise.resolve(null),
                    getDeals({
                        contact_id: contactId,
                        limit: 10,
                        offset: 0,
                    }),
                ]);

                if (!isMounted) {
                    return;
                }

                setContact(contactResponse);

                if (companyResult.status === "fulfilled") {
                    setCompany(companyResult.value);
                } else {
                    console.warn("Failed to load contact company:", companyResult.reason);
                    setRelatedWarning("Some related records could not be loaded.");
                }

                if (dealsResult.status === "fulfilled") {
                    setRelatedDeals(dealsResult.value.items ?? []);
                } else {
                    console.warn("Failed to load contact deals:", dealsResult.reason);
                    setRelatedWarning("Some related records could not be loaded.");
                }
            } catch (error) {
                console.error("Failed to load contact detail:", error);
                if (!isMounted) {
                    return;
                }

                setContact(null);
                setCompany(null);
                setErrorMessage(getLoadErrorMessage(error));
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadContactDetail();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, contactId]);

    async function handleDeleteContact(): Promise<void> {
        if (!contact) {
            return;
        }

        const confirmed = window.confirm(
            `Delete ${formatContactName(contact)}? This action cannot be undone.`,
        );
        if (!confirmed) {
            return;
        }

        try {
            setIsDeleting(true);
            setDeleteError("");
            await deleteContact(contact.id);
            router.push("/contacts");
            router.refresh();
        } catch (error) {
            console.error("Failed to delete contact:", error);
            setDeleteError(getActionErrorMessage(error, "Failed to delete contact."));
        } finally {
            setIsDeleting(false);
        }
    }

    const detailRows = useMemo<Array<{ label: string; value: ReactNode }>>(() => {
        if (!contact) {
            return [];
        }

        const companyValue: ReactNode = contact.company_id ? (
            <Link
                href={`/companies/${contact.company_id}`}
                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
            >
                {company?.name ?? contact.company ?? contact.company_id}
            </Link>
        ) : (
            contact.company ?? "No company"
        );

        return [
            { label: "Contact Name", value: formatContactName(contact) },
            { label: "Email", value: contact.email ?? "Not set" },
            { label: "Phone", value: contact.phone ?? "Not set" },
            { label: "Company", value: companyValue },
            { label: "Job Title", value: contact.job_title ?? "Not set" },
            { label: "Notes", value: contact.notes?.trim() ? contact.notes : "No notes" },
            { label: "Created At", value: formatDateTime(contact.created_at) },
            { label: "Updated At", value: formatDateTime(contact.updated_at) },
        ];
    }, [company, contact]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">
                            {contact ? formatContactName(contact) : "Contact Details"}
                        </h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Review contact details and move qualified people into the live Lead to Deal flow.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {contact?.company_id ? (
                            <Link
                                href={buildLeadCreateHref({
                                    companyId: contact.company_id,
                                    contactId: contact.id,
                                })}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                            >
                                Create Lead
                            </Link>
                        ) : (
                            <span className="rounded-lg border border-slate-200 bg-slate-100 px-4 py-2 text-sm font-medium text-slate-500">
                                Assign a company to create a lead
                            </span>
                        )}
                        <Link
                            href={contactId ? `/contacts/${contactId}/edit` : "/contacts"}
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Edit Contact
                        </Link>
                        <Link
                            href="/contacts"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all contacts
                        </Link>
                        <button
                            type="button"
                            onClick={() => {
                                void handleDeleteContact();
                            }}
                            disabled={isDeleting || !contact}
                            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isDeleting ? "Deleting..." : "Delete contact"}
                        </button>
                    </div>
                </div>

                {deleteError ? (
                    <p className="mt-4 text-sm text-red-700">{deleteError}</p>
                ) : null}
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading contact details</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching contact, related company, and related deals from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load contact</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !contact ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Contact unavailable</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested contact could not be found.
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

                    {relatedWarning ? (
                        <section className="rounded-xl border border-amber-200 bg-white p-4 shadow-sm">
                            <p className="text-sm text-amber-700">{relatedWarning}</p>
                        </section>
                    ) : null}

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Related Deals</h2>
                        <p className="mt-2 text-sm text-slate-600">
                            Deals already linked to this contact on the current Sales backbone.
                        </p>

                        {relatedDeals.length === 0 ? (
                            <p className="mt-4 text-sm text-slate-600">No deals found for this contact.</p>
                        ) : (
                            <ul className="mt-4 space-y-2">
                                {relatedDeals.map((deal) => (
                                    <li
                                        key={deal.id}
                                        className="rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-700"
                                    >
                                        <Link
                                            href={`/deals/${deal.id}`}
                                            className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
                                        >
                                            {deal.name}
                                        </Link>
                                        <span className="ml-2 text-slate-500">
                                            {formatDealLabel(deal.stage)} · {formatMoney(deal.amount, deal.currency)} · {formatDealLabel(deal.status)}
                                        </span>
                                        {deal.expected_close_date ? (
                                            <span className="ml-2 text-slate-500">
                                                (Expected {formatDate(deal.expected_close_date)})
                                            </span>
                                        ) : null}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>
                </>
            )}
        </main>
    );
}

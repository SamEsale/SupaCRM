"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { formatCompanyAddress } from "@/components/crm/company-address-utils";
import { buildLeadCreateHref, formatDealLabel } from "@/lib/deals";
import { deleteCompany, getCompanyById } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
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
            return "Company not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The company could not be loaded from the backend.";
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

export default function CompanyDetailPage() {
    const auth = useAuth();
    const router = useRouter();
    const params = useParams<{ companyId: string }>();
    const rawCompanyId = params?.companyId;
    const companyId = Array.isArray(rawCompanyId) ? rawCompanyId[0] : rawCompanyId;

    const [company, setCompany] = useState<Company | null>(null);
    const [relatedContacts, setRelatedContacts] = useState<Contact[]>([]);
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

        if (!companyId) {
            setErrorMessage("Invalid company id.");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadCompanyDetail(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                setRelatedWarning("");
                setRelatedContacts([]);
                setRelatedDeals([]);

                const companyResponse = await getCompanyById(companyId);

                const [contactsResult, dealsResult] = await Promise.allSettled([
                    getContacts({
                        company_id: companyId,
                        limit: 10,
                        offset: 0,
                    }),
                    getDeals({
                        company_id: companyId,
                        limit: 10,
                        offset: 0,
                    }),
                ]);

                if (!isMounted) {
                    return;
                }

                setCompany(companyResponse);

                if (contactsResult.status === "fulfilled") {
                    setRelatedContacts(contactsResult.value.items ?? []);
                } else {
                    console.warn("Failed to load company contacts:", contactsResult.reason);
                    setRelatedWarning("Some related records could not be loaded.");
                }

                if (dealsResult.status === "fulfilled") {
                    setRelatedDeals(dealsResult.value.items ?? []);
                } else {
                    console.warn("Failed to load company deals:", dealsResult.reason);
                    setRelatedWarning("Some related records could not be loaded.");
                }
            } catch (error) {
                console.error("Failed to load company detail:", error);
                if (!isMounted) {
                    return;
                }

                setCompany(null);
                setErrorMessage(getLoadErrorMessage(error));
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadCompanyDetail();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, companyId]);

    async function handleDeleteCompany(): Promise<void> {
        if (!company) {
            return;
        }

        const confirmed = window.confirm(
            `Delete ${company.name}? This action cannot be undone.`,
        );
        if (!confirmed) {
            return;
        }

        try {
            setIsDeleting(true);
            setDeleteError("");
            await deleteCompany(company.id);
            router.push("/companies");
            router.refresh();
        } catch (error) {
            console.error("Failed to delete company:", error);
            setDeleteError(getActionErrorMessage(error, "Failed to delete company."));
        } finally {
            setIsDeleting(false);
        }
    }

    const detailRows = useMemo(() => {
        if (!company) {
            return [];
        }

        return [
            { label: "Company Name", value: company.name },
            { label: "Website", value: company.website ?? "Not set" },
            { label: "Email", value: company.email ?? "Not set" },
            { label: "Phone", value: company.phone ?? "Not set" },
            { label: "Industry", value: company.industry ?? "Not set" },
            {
                label: "Address",
                value: company.address ? formatCompanyAddress(company.address) : "Not set",
            },
            { label: "VAT Number", value: company.vat_number ?? "Not set" },
            { label: "Registration Number", value: company.registration_number ?? "Not set" },
            { label: "Notes", value: company.notes?.trim() ? company.notes : "No notes" },
            { label: "Created At", value: formatDateTime(company.created_at) },
            { label: "Updated At", value: formatDateTime(company.updated_at) },
        ];
    }, [company]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">
                            {company ? company.name : "Company Details"}
                        </h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Review company context, related contacts, and move the account into the live Lead to Deal workflow.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        <Link
                            href={buildLeadCreateHref({
                                companyId: company?.id ?? companyId ?? null,
                            })}
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Create Lead
                        </Link>
                        <Link
                            href={companyId ? `/companies/${companyId}/edit` : "/companies"}
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Edit Company
                        </Link>
                        <Link
                            href="/companies"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all companies
                        </Link>
                        <button
                            type="button"
                            onClick={() => {
                                void handleDeleteCompany();
                            }}
                            disabled={isDeleting || !company}
                            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isDeleting ? "Deleting..." : "Delete company"}
                        </button>
                    </div>
                </div>

                {deleteError ? (
                    <p className="mt-4 text-sm text-red-700">{deleteError}</p>
                ) : null}
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading company details</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching company, related contacts, and related deals from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load company</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !company ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Company unavailable</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested company could not be found.
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
                        <h2 className="text-xl font-semibold text-slate-900">Recent Contacts</h2>
                        <p className="mt-2 text-sm text-slate-600">
                            Contacts linked to this company.
                        </p>

                        {relatedContacts.length === 0 ? (
                            <p className="mt-4 text-sm text-slate-600">No contacts found for this company.</p>
                        ) : (
                            <ul className="mt-4 space-y-2">
                                {relatedContacts.map((contact) => (
                                    <li
                                        key={contact.id}
                                        className="rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-700"
                                    >
                                        <Link
                                            href={`/contacts/${contact.id}`}
                                            className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
                                        >
                                            {formatContactName(contact)}
                                        </Link>
                                        {contact.job_title ? ` - ${contact.job_title}` : ""}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Company Deals</h2>
                        <p className="mt-2 text-sm text-slate-600">
                            Deals already linked to this company on the current Sales backbone.
                        </p>

                        {relatedDeals.length === 0 ? (
                            <p className="mt-4 text-sm text-slate-600">No deals found for this company.</p>
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

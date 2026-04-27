"use client";

import axios from "axios";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import SupportTicketForm from "@/components/support/SupportTicketForm";
import { useAuth } from "@/hooks/use-auth";
import {
    buildSupportTicketUpdatePayload,
    formatSupportLabel,
    formatSupportTimestamp,
    getSupportPriorityClasses,
    getSupportStatusClasses,
} from "@/lib/support";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals } from "@/services/deals.service";
import { getInvoices } from "@/services/invoices.service";
import { getSupportTicketById, updateSupportTicket } from "@/services/support.service";
import { getTenantUsers } from "@/services/tenants.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Invoice } from "@/types/finance";
import type { SupportTicket, SupportTicketCreateRequest } from "@/types/support";
import type { TenantUser } from "@/types/tenants";

function getLoadErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Ticket not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The support ticket could not be loaded from the backend.";
}

export default function SupportTicketDetailPage() {
    const auth = useAuth();
    const params = useParams<{ ticketId: string }>();
    const rawTicketId = params?.ticketId;
    const ticketId = Array.isArray(rawTicketId) ? rawTicketId[0] : rawTicketId;

    const [ticket, setTicket] = useState<SupportTicket | null>(null);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [tenantUsers, setTenantUsers] = useState<TenantUser[]>([]);
    const [deals, setDeals] = useState<Deal[]>([]);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        if (!ticketId) {
            setErrorMessage("Invalid ticket id.");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadTicketDetail(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const [
                    ticketResponse,
                    companiesResponse,
                    contactsResponse,
                    tenantUsersResponse,
                    dealsResponse,
                    invoicesResponse,
                ] = await Promise.all([
                    getSupportTicketById(ticketId),
                    getCompanies(),
                    getContacts(),
                    getTenantUsers(),
                    getDeals({ limit: 100 }),
                    getInvoices({ limit: 100 }),
                ]);

                if (!isMounted) {
                    return;
                }

                setTicket(ticketResponse);
                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setTenantUsers(tenantUsersResponse ?? []);
                setDeals(dealsResponse.items ?? []);
                setInvoices(invoicesResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load support ticket detail:", error);
                if (!isMounted) {
                    return;
                }

                setErrorMessage(getLoadErrorMessage(error));
                setTicket(null);
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadTicketDetail();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, ticketId]);

    const initialValues = useMemo(() => {
        if (!ticket) {
            return undefined;
        }

        return buildSupportTicketUpdatePayload(ticket);
    }, [ticket]);

    async function handleSave(payload: SupportTicketCreateRequest): Promise<SupportTicket> {
        if (!ticketId) {
            throw new Error("Invalid ticket id.");
        }

        const updated = await updateSupportTicket(ticketId, payload);
        setTicket(updated);
        return updated;
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">{ticket?.title ?? "Ticket Detail"}</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Keep the ticket current while preserving linked customer, sales, and invoice context.
                        </p>
                        {ticket ? (
                            <div className="mt-4 flex flex-wrap gap-2">
                                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${getSupportStatusClasses(ticket.status)}`}>
                                    {formatSupportLabel(ticket.status)}
                                </span>
                                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${getSupportPriorityClasses(ticket.priority)}`}>
                                    {formatSupportLabel(ticket.priority)}
                                </span>
                                <span className="inline-flex rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                                    {formatSupportLabel(ticket.source)}
                                </span>
                            </div>
                        ) : null}
                    </div>
                    <Link
                        href="/support"
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Back to all tickets
                    </Link>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading ticket detail</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching the ticket, CRM references, tenant users, deals, and invoices from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load ticket detail</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !ticket ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Ticket unavailable</h2>
                    <p className="mt-2 text-sm text-slate-600">The requested support ticket could not be found.</p>
                </section>
            ) : (
                <>
                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Linked Context</h2>
                        <dl className="mt-6 grid gap-4 md:grid-cols-2">
                            <div>
                                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Company</dt>
                                <dd className="mt-2 text-sm text-slate-900">
                                    {ticket.company_id ? (
                                        <Link href={`/companies/${ticket.company_id}`} className="font-medium underline underline-offset-2">
                                            {ticket.company_name ?? ticket.company_id}
                                        </Link>
                                    ) : (
                                        "No company linked"
                                    )}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Contact</dt>
                                <dd className="mt-2 text-sm text-slate-900">
                                    {ticket.contact_id ? (
                                        <Link href={`/contacts/${ticket.contact_id}`} className="font-medium underline underline-offset-2">
                                            {ticket.contact_name ?? ticket.contact_id}
                                        </Link>
                                    ) : (
                                        "No contact linked"
                                    )}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Related deal</dt>
                                <dd className="mt-2 text-sm text-slate-900">
                                    {ticket.related_deal_id ? (
                                        <Link href={`/deals/${ticket.related_deal_id}`} className="font-medium underline underline-offset-2">
                                            {ticket.related_deal_name ?? ticket.related_deal_id}
                                        </Link>
                                    ) : (
                                        "No related deal"
                                    )}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Related invoice</dt>
                                <dd className="mt-2 text-sm text-slate-900">
                                    {ticket.related_invoice_id ? (
                                        <Link href={`/finance/invoices/${ticket.related_invoice_id}`} className="font-medium underline underline-offset-2">
                                            {ticket.related_invoice_number ?? ticket.related_invoice_id}
                                        </Link>
                                    ) : (
                                        "No related invoice"
                                    )}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Assigned to</dt>
                                <dd className="mt-2 text-sm text-slate-900">
                                    {ticket.assigned_to_user_id ? (
                                        ticket.assigned_to_full_name ?? ticket.assigned_to_email ?? ticket.assigned_to_user_id
                                    ) : (
                                        "Unassigned"
                                    )}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Last updated</dt>
                                <dd className="mt-2 text-sm text-slate-900">{formatSupportTimestamp(ticket.updated_at)}</dd>
                            </div>
                        </dl>
                    </section>

                    <SupportTicketForm
                        mode="edit"
                        companies={companies}
                        contacts={contacts}
                        tenantUsers={tenantUsers}
                        deals={deals}
                        invoices={invoices}
                        initialValues={initialValues}
                        onSubmit={handleSave}
                        onSuccess={(updated) => {
                            setTicket(updated);
                        }}
                        title="Update ticket"
                        description="Adjust ticket status, priority, ownership, and linked CRM or commercial context."
                        submitLabel="Save changes"
                        submittingLabel="Saving..."
                        successMessage="Ticket updated successfully."
                    />
                </>
            )}
        </main>
    );
}

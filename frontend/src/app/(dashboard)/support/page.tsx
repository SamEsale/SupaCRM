"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import {
    formatSupportLabel,
    formatSupportTimestamp,
    getSupportPriorityClasses,
    getSupportStatusClasses,
    SUPPORT_TICKET_PRIORITIES,
    SUPPORT_TICKET_STATUSES,
} from "@/lib/support";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getSupportSummary, getSupportTickets } from "@/services/support.service";
import type { Company, Contact } from "@/types/crm";
import type { SupportSummary, SupportTicket, SupportTicketPriority, SupportTicketStatus } from "@/types/support";

function buildCompanyName(ticket: SupportTicket, companies: Company[]): string {
    if (!ticket.company_id) {
        return "No company";
    }

    return companies.find((company) => company.id === ticket.company_id)?.name ?? ticket.company_name ?? ticket.company_id;
}

function buildContactName(ticket: SupportTicket, contacts: Contact[]): string {
    if (!ticket.contact_id) {
        return "No contact";
    }

    const contact = contacts.find((item) => item.id === ticket.contact_id);
    if (contact) {
        return [contact.first_name, contact.last_name].filter(Boolean).join(" ");
    }

    return ticket.contact_name ?? ticket.contact_id;
}

export default function SupportPage() {
    const auth = useAuth();
    const [tickets, setTickets] = useState<SupportTicket[]>([]);
    const [total, setTotal] = useState<number>(0);
    const [summary, setSummary] = useState<SupportSummary | null>(null);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [searchInput, setSearchInput] = useState<string>("");
    const [statusFilter, setStatusFilter] = useState<"" | SupportTicketStatus>("");
    const [priorityFilter, setPriorityFilter] = useState<"" | SupportTicketPriority>("");
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    const loadSupportWorkspace = useCallback(async (): Promise<void> => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        try {
            setIsLoading(true);
            setErrorMessage("");

            const [ticketsResponse, summaryResponse, companiesResponse, contactsResponse] =
                await Promise.all([
                    getSupportTickets({
                        q: searchInput.trim() || undefined,
                        status: statusFilter || undefined,
                        priority: priorityFilter || undefined,
                    }),
                    getSupportSummary(),
                    getCompanies(),
                    getContacts(),
                ]);

            setTickets(ticketsResponse.items ?? []);
            setTotal(ticketsResponse.total ?? 0);
            setSummary(summaryResponse);
            setCompanies(companiesResponse.items ?? []);
            setContacts(contactsResponse.items ?? []);
        } catch (error) {
            console.error("Failed to load support workspace:", error);
            setErrorMessage("The support workspace could not be loaded from the backend.");
        } finally {
            setIsLoading(false);
        }
    }, [
        auth.accessToken,
        auth.isAuthenticated,
        auth.isReady,
        priorityFilter,
        searchInput,
        statusFilter,
    ]);

    useEffect(() => {
        void loadSupportWorkspace();
    }, [loadSupportWorkspace]);

    const hasFilters = useMemo(() => {
        return Boolean(searchInput.trim() || statusFilter || priorityFilter);
    }, [priorityFilter, searchInput, statusFilter]);

    function clearFilters(): void {
        setSearchInput("");
        setStatusFilter("");
        setPriorityFilter("");
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Support</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Track tenant-scoped tickets, keep CRM context visible, and move customer issues forward without leaving the platform.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/contacts"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Customer Contacts
                        </Link>
                        <Link
                            href="/support/create"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Create Ticket
                        </Link>
                    </div>
                </div>
            </section>

            {summary ? (
                <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Open Tickets</p>
                        <p className="mt-2 text-3xl font-semibold text-slate-900">{summary.open_count}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">In Progress</p>
                        <p className="mt-2 text-3xl font-semibold text-slate-900">{summary.in_progress_count}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Urgent Active</p>
                        <p className="mt-2 text-3xl font-semibold text-slate-900">{summary.urgent_count}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Resolved This Period</p>
                        <p className="mt-2 text-3xl font-semibold text-slate-900">{summary.resolved_this_period_count}</p>
                    </div>
                </section>
            ) : null}

            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-end gap-3">
                    <div className="min-w-64 flex-1">
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-search">
                            Search tickets
                        </label>
                        <input
                            id="support-search"
                            value={searchInput}
                            onChange={(event) => setSearchInput(event.target.value)}
                            placeholder="Search title, description, company, contact, or assignee"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-status-filter">
                            Status
                        </label>
                        <select
                            id="support-status-filter"
                            value={statusFilter}
                            onChange={(event) =>
                                setStatusFilter(event.target.value as "" | SupportTicketStatus)
                            }
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                        >
                            <option value="">All statuses</option>
                            {SUPPORT_TICKET_STATUSES.map((status) => (
                                <option key={status} value={status}>
                                    {formatSupportLabel(status)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-priority-filter">
                            Priority
                        </label>
                        <select
                            id="support-priority-filter"
                            value={priorityFilter}
                            onChange={(event) =>
                                setPriorityFilter(event.target.value as "" | SupportTicketPriority)
                            }
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                        >
                            <option value="">All priorities</option>
                            {SUPPORT_TICKET_PRIORITIES.map((priority) => (
                                <option key={priority} value={priority}>
                                    {formatSupportLabel(priority)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <button
                        type="button"
                        onClick={() => {
                            void loadSupportWorkspace();
                        }}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                    >
                        Apply Filters
                    </button>

                    {hasFilters ? (
                        <button
                            type="button"
                            onClick={() => {
                                clearFilters();
                            }}
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Clear
                        </button>
                    ) : null}
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading support workspace</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching tickets, CRM links, and the operator summary from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load support workspace</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                    <button
                        type="button"
                        onClick={() => {
                            void loadSupportWorkspace();
                        }}
                        className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Retry
                    </button>
                </section>
            ) : tickets.length === 0 ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">No tickets found</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        No support tickets matched the current filters for this tenant.
                    </p>
                </section>
            ) : (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <h2 className="text-2xl font-semibold text-slate-900">All Tickets</h2>
                            <p className="mt-2 text-sm text-slate-600">{total} tickets loaded from the backend API.</p>
                        </div>
                    </div>

                    <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
                        <table className="min-w-full border-collapse">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Ticket</th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Priority</th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Company</th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Contact</th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">Updated</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tickets.map((ticket) => (
                                    <tr key={ticket.id} className="align-top hover:bg-slate-50">
                                        <td className="px-4 py-3 text-sm">
                                            <Link
                                                href={`/support/${ticket.id}`}
                                                className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
                                            >
                                                {ticket.title}
                                            </Link>
                                            <p className="mt-1 text-xs text-slate-500">{formatSupportLabel(ticket.source)}</p>
                                        </td>
                                        <td className="px-4 py-3 text-sm">
                                            <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${getSupportStatusClasses(ticket.status)}`}>
                                                {formatSupportLabel(ticket.status)}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-sm">
                                            <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${getSupportPriorityClasses(ticket.priority)}`}>
                                                {formatSupportLabel(ticket.priority)}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-sm">
                                            {ticket.company_id ? (
                                                <Link
                                                    href={`/companies/${ticket.company_id}`}
                                                    className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
                                                >
                                                    {buildCompanyName(ticket, companies)}
                                                </Link>
                                            ) : (
                                                "No company"
                                            )}
                                        </td>
                                        <td className="px-4 py-3 text-sm">
                                            {ticket.contact_id ? (
                                                <Link
                                                    href={`/contacts/${ticket.contact_id}`}
                                                    className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
                                                >
                                                    {buildContactName(ticket, contacts)}
                                                </Link>
                                            ) : (
                                                "No contact"
                                            )}
                                        </td>
                                        <td className="px-4 py-3 text-sm text-slate-600">
                                            {formatSupportTimestamp(ticket.updated_at)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>
            )}
        </main>
    );
}

"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
    formatDealLabel,
    getDealFollowUpLabel,
    getDealFollowUpState,
    getOpportunityAttentionReason,
} from "@/lib/deals";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals, getSalesForecastReport } from "@/services/deals.service";
import type { Company, Contact, Deal, SalesForecastReportResponse } from "@/types/crm";

type SalesReportSnapshot = {
    report: SalesForecastReportResponse;
    deals: Deal[];
    opportunities: Deal[];
    companies: Company[];
    contacts: Contact[];
};

function formatMoney(amount: string, currency?: string): string {
    const value = Number(amount);
    if (Number.isNaN(value)) {
        return currency ? `${amount} ${currency}` : amount;
    }

    if (!currency) {
        return new Intl.NumberFormat("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(value);
}

function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

function formatDate(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleDateString("en-US");
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
    return [contact.first_name, contact.last_name].filter(Boolean).join(" ");
}

function parseApiError(error: unknown, fallback: string): string {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
            return response.data.detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return fallback;
}

async function loadSalesReportSnapshot(): Promise<SalesReportSnapshot> {
    const [report, dealsResponse, opportunitiesResponse, companiesResponse, contactsResponse] =
        await Promise.all([
            getSalesForecastReport(),
            getDeals({ limit: 200, offset: 0 }),
            getDeals({ view: "opportunities", limit: 200, offset: 0 }),
            getCompanies(),
            getContacts(),
        ]);

    return {
        report,
        deals: dealsResponse.items ?? [],
        opportunities: opportunitiesResponse.items ?? [],
        companies: companiesResponse.items ?? [],
        contacts: contactsResponse.items ?? [],
    };
}

export default function SalesReportsPage() {
    const [snapshot, setSnapshot] = useState<SalesReportSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [searchTerm, setSearchTerm] = useState<string>("");
    const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
    const displayCurrency = snapshot?.report.summary.currencies.length === 1
        ? snapshot.report.summary.currencies[0]
        : undefined;

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");
            const nextSnapshot = await loadSalesReportSnapshot();
            setSnapshot(nextSnapshot);
        } catch (error) {
            console.error("Failed to load sales reports:", error);
            setErrorMessage(
                parseApiError(error, "The sales reporting view could not be loaded from the backend."),
            );
            setSnapshot(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadSnapshot();
    }, [loadSnapshot]);

    const overdueFollowUps = useMemo(() => {
        if (!snapshot) {
            return [];
        }

        return snapshot.deals.filter((deal) => {
            const matchesSearch = searchTerm.trim() === ""
                || [
                    deal.name,
                    getCompanyName(snapshot.companies, deal.company_id),
                    getContactName(snapshot.contacts, deal.contact_id),
                ].join(" ").toLowerCase().includes(searchTerm.trim().toLowerCase());
            const matchesCompany = selectedCompanyId === "" || deal.company_id === selectedCompanyId;
            return matchesSearch && matchesCompany && getDealFollowUpState(deal) === "overdue";
        });
    }, [searchTerm, selectedCompanyId, snapshot]);

    const attentionOpportunities = useMemo(() => {
        if (!snapshot) {
            return [];
        }

        return snapshot.opportunities.filter((deal) => {
            const matchesSearch = searchTerm.trim() === ""
                || [
                    deal.name,
                    getCompanyName(snapshot.companies, deal.company_id),
                    getContactName(snapshot.contacts, deal.contact_id),
                ].join(" ").toLowerCase().includes(searchTerm.trim().toLowerCase());
            const matchesCompany = selectedCompanyId === "" || deal.company_id === selectedCompanyId;
            return matchesSearch && matchesCompany && getOpportunityAttentionReason(deal) !== null;
        });
    }, [searchTerm, selectedCompanyId, snapshot]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Sales Reports</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Forecast the weighted pipeline, monitor closed revenue, and work the deals that need immediate follow-up.
                </p>
                {snapshot && snapshot.report.summary.currencies.length > 1 ? (
                    <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                        Totals currently span multiple deal currencies ({snapshot.report.summary.currencies.join(", ")}) and are not FX-normalized.
                    </p>
                ) : null}

                <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(event) => setSearchTerm(event.target.value)}
                        placeholder="Filter attention lists by deal, company, or contact"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />

                    <select
                        value={selectedCompanyId}
                        onChange={(event) => setSelectedCompanyId(event.target.value)}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    >
                        <option value="">All companies</option>
                        {snapshot?.companies.map((company) => (
                            <option key={company.id} value={company.id}>
                                {company.name}
                            </option>
                        )) ?? null}
                    </select>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading sales reports</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching forecasting metrics, deal breakdowns, and follow-up attention lists from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load sales reports</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                    <button
                        type="button"
                        onClick={() => {
                            void loadSnapshot();
                        }}
                        className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Retry
                    </button>
                </section>
            ) : snapshot ? (
                <>
                    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Open pipeline</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {formatMoney(snapshot.report.summary.total_open_pipeline_amount, displayCurrency)}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                Total amount across open and in-progress deals.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Weighted pipeline</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {formatMoney(snapshot.report.summary.weighted_pipeline_amount, displayCurrency)}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                Probability-weighted using the current deal stage model.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Overdue follow-ups</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {snapshot.report.summary.overdue_follow_up_count}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.report.summary.due_today_follow_up_count} due today, {snapshot.report.summary.upcoming_follow_up_count} upcoming.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Won this period</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {formatMoney(snapshot.report.summary.deals_won_this_period_amount, displayCurrency)}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.report.summary.deals_won_this_period_count} deals closed won since {formatDate(snapshot.report.summary.report_period_start)}.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Lost this period</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                                {formatMoney(snapshot.report.summary.deals_lost_this_period_amount, displayCurrency)}
                            </p>
                            <p className="mt-2 text-sm text-slate-600">
                                {snapshot.report.summary.deals_lost_this_period_count} deals closed lost since {formatDate(snapshot.report.summary.report_period_start)}.
                            </p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Closed amounts</p>
                            <p className="mt-3 text-lg font-bold text-slate-900">
                                Won {formatMoney(snapshot.report.summary.won_amount, displayCurrency)}
                            </p>
                            <p className="mt-1 text-sm text-slate-600">
                                Lost {formatMoney(snapshot.report.summary.lost_amount, displayCurrency)}
                            </p>
                        </article>
                    </section>

                    <section className="grid gap-6 xl:grid-cols-2">
                        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Pipeline by stage</h2>
                            <p className="mt-2 text-sm text-slate-600">
                                Full-stage breakdown using the current deals pipeline and explicit weighting model.
                            </p>

                            <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
                                <table className="min-w-full border-collapse">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Stage</th>
                                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Deals</th>
                                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Open amount</th>
                                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Weighted</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {snapshot.report.stage_breakdown.map((item) => (
                                            <tr key={item.stage}>
                                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-900">{formatDealLabel(item.stage)}</td>
                                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">{item.count}</td>
                                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">{formatMoney(item.open_amount, displayCurrency)}</td>
                                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">{formatMoney(item.weighted_amount, displayCurrency)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>

                        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Open opportunities by stage</h2>
                            <p className="mt-2 text-sm text-slate-600">
                                Opportunity-only view across qualified, proposal, estimate, and negotiation stages.
                            </p>

                            <div className="mt-6 space-y-3">
                                {snapshot.report.opportunity_stage_breakdown.map((item) => (
                                    <div
                                        key={item.stage}
                                        className="rounded-lg border border-slate-200 p-4"
                                    >
                                        <div className="flex items-center justify-between gap-3">
                                            <div>
                                                <h3 className="text-sm font-semibold text-slate-900">
                                                    {formatDealLabel(item.stage)}
                                                </h3>
                                                <p className="mt-1 text-sm text-slate-600">
                                                    {item.count} deal{item.count === 1 ? "" : "s"} in this opportunity stage
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm font-semibold text-slate-900">{formatMoney(item.open_amount, displayCurrency)}</p>
                                                <p className="mt-1 text-xs text-slate-500">Weighted {formatMoney(item.weighted_amount, displayCurrency)}</p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </section>

                    <section className="grid gap-6 xl:grid-cols-2">
                        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Overdue follow-ups</h2>
                            <p className="mt-2 text-sm text-slate-600">
                                Deals that need immediate outreach based on the next follow-up date stored on the deal.
                            </p>

                            {overdueFollowUps.length === 0 ? (
                                <p className="mt-4 text-sm text-slate-600">No overdue follow-ups matched the current filters.</p>
                            ) : (
                                <div className="mt-4 space-y-3">
                                    {overdueFollowUps.map((deal) => (
                                        <div key={deal.id} className="rounded-lg border border-red-200 bg-red-50 p-4">
                                            <div className="flex flex-wrap items-center justify-between gap-3">
                                                <div>
                                                    <Link href={`/deals/${deal.id}`} className="text-sm font-semibold text-slate-900 underline underline-offset-2">
                                                        {deal.name}
                                                    </Link>
                                                    <p className="mt-1 text-sm text-slate-600">
                                                        {getCompanyName(snapshot.companies, deal.company_id)} • {getContactName(snapshot.contacts, deal.contact_id)}
                                                    </p>
                                                    <p className="mt-2 text-xs text-red-700">
                                                        {getDealFollowUpLabel(deal)} since {deal.next_follow_up_at ? formatDateTime(deal.next_follow_up_at) : "not scheduled"}
                                                    </p>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-sm font-semibold text-slate-900">
                                                        {formatMoney(deal.amount, deal.currency)}
                                                    </p>
                                                    <p className="mt-1 text-xs text-slate-500">{formatDealLabel(deal.stage)}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>

                        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Opportunities requiring attention</h2>
                            <p className="mt-2 text-sm text-slate-600">
                                Active opportunities with overdue, due-today, or unscheduled follow-up work.
                            </p>

                            {attentionOpportunities.length === 0 ? (
                                <p className="mt-4 text-sm text-slate-600">No active opportunities currently require attention.</p>
                            ) : (
                                <div className="mt-4 space-y-3">
                                    {attentionOpportunities.map((deal) => (
                                        <div key={deal.id} className="rounded-lg border border-slate-200 p-4">
                                            <div className="flex flex-wrap items-center justify-between gap-3">
                                                <div>
                                                    <Link href={`/deals/${deal.id}`} className="text-sm font-semibold text-slate-900 underline underline-offset-2">
                                                        {deal.name}
                                                    </Link>
                                                    <p className="mt-1 text-sm text-slate-600">
                                                        {getCompanyName(snapshot.companies, deal.company_id)} • {getContactName(snapshot.contacts, deal.contact_id)}
                                                    </p>
                                                    <p className="mt-2 text-xs text-slate-500">
                                                        {getOpportunityAttentionReason(deal)} • {deal.next_follow_up_at ? formatDateTime(deal.next_follow_up_at) : "No follow-up scheduled"}
                                                    </p>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-sm font-semibold text-slate-900">
                                                        {formatMoney(deal.amount, deal.currency)}
                                                    </p>
                                                    <p className="mt-1 text-xs text-slate-500">{formatDealLabel(deal.stage)}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>
                    </section>
                </>
            ) : null}
        </main>
    );
}

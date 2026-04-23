"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage, getApiErrorStatus } from "@/lib/api-errors";
import { getRecentAuditActivity } from "@/services/audit.service";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals, getSalesForecastReport } from "@/services/deals.service";
import { getMarketingCampaigns } from "@/services/marketing.service";
import { getFinanceReportsSnapshot, type FinanceReportsSnapshot } from "@/services/reporting.service";
import { getSupportSummary } from "@/services/support.service";
import type { RecentAuditActivity } from "@/types/audit";
import type { SalesForecastReportResponse } from "@/types/crm";
import type { SupportSummary } from "@/types/support";

type DashboardSnapshot = {
    companiesTotal: number | null;
    contactsTotal: number | null;
    dealsTotal: number | null;
    salesReport: SalesForecastReportResponse | null;
    supportSummary: SupportSummary | null;
    financeSnapshot: FinanceReportsSnapshot | null;
    campaignTotal: number | null;
    recentActivity: RecentAuditActivity[];
};

type DashboardCard = {
    title: string;
    value: string;
    description: string;
    href: string;
};

const EMPTY_SNAPSHOT: DashboardSnapshot = {
    companiesTotal: null,
    contactsTotal: null,
    dealsTotal: null,
    salesReport: null,
    supportSummary: null,
    financeSnapshot: null,
    campaignTotal: null,
    recentActivity: [],
};

function formatCount(value: number): string {
    return new Intl.NumberFormat("en-US").format(value);
}

function formatMoney(amount: string, currency: string): string {
    const parsed = Number(amount);
    if (Number.isNaN(parsed)) {
        return `${amount} ${currency}`;
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(parsed);
}

function formatMixedCurrencySummary(currencies: string[]): string {
    if (currencies.length === 0) {
        return "No currency data";
    }

    if (currencies.length === 1) {
        return currencies[0];
    }

    return `Mixed currencies (${currencies.join(", ")})`;
}

function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }

    return parsed.toLocaleString("en-US");
}

function formatActionLabel(value: string): string {
    return value
        .replace(/[._]/g, " ")
        .split(" ")
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function buildSectionWarning(label: string, error: unknown): string {
    const status = getApiErrorStatus(error);

    if (status === 401 || status === 403) {
        return `${label} widgets are hidden for this account.`;
    }

    return getApiErrorMessage(error, `${label} widgets could not be loaded right now.`);
}

export default function DashboardPage() {
    const auth = useAuth();
    const [snapshot, setSnapshot] = useState<DashboardSnapshot>(EMPTY_SNAPSHOT);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [warnings, setWarnings] = useState<string[]>([]);

    const loadDashboard = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");

            const [
                companiesResult,
                contactsResult,
                dealsResult,
                salesReportResult,
                supportSummaryResult,
                financeSnapshotResult,
                campaignsResult,
                activityResult,
            ] = await Promise.allSettled([
                getCompanies(),
                getContacts({ limit: 1, offset: 0 }),
                getDeals({ limit: 1, offset: 0 }),
                getSalesForecastReport(),
                getSupportSummary(),
                getFinanceReportsSnapshot(),
                getMarketingCampaigns({ limit: 1, offset: 0 }),
                getRecentAuditActivity(10),
            ]);

            const nextSnapshot: DashboardSnapshot = { ...EMPTY_SNAPSHOT };
            const nextWarnings: string[] = [];
            let successfulSections = 0;

            if (companiesResult.status === "fulfilled") {
                nextSnapshot.companiesTotal = companiesResult.value.total;
                successfulSections += 1;
            } else {
                nextWarnings.push(buildSectionWarning("CRM company", companiesResult.reason));
            }

            if (contactsResult.status === "fulfilled") {
                nextSnapshot.contactsTotal = contactsResult.value.total;
                successfulSections += 1;
            } else {
                nextWarnings.push(buildSectionWarning("CRM contact", contactsResult.reason));
            }

            if (dealsResult.status === "fulfilled") {
                nextSnapshot.dealsTotal = dealsResult.value.total;
                successfulSections += 1;
            } else {
                nextWarnings.push(buildSectionWarning("Sales deal", dealsResult.reason));
            }

            if (salesReportResult.status === "fulfilled") {
                nextSnapshot.salesReport = salesReportResult.value;
                successfulSections += 1;
            } else {
                nextWarnings.push(buildSectionWarning("Sales forecasting", salesReportResult.reason));
            }

            if (supportSummaryResult.status === "fulfilled") {
                nextSnapshot.supportSummary = supportSummaryResult.value;
                successfulSections += 1;
            } else {
                nextWarnings.push(buildSectionWarning("Support summary", supportSummaryResult.reason));
            }

            if (financeSnapshotResult.status === "fulfilled") {
                nextSnapshot.financeSnapshot = financeSnapshotResult.value;
                successfulSections += 1;
            } else {
                nextWarnings.push(buildSectionWarning("Finance reporting", financeSnapshotResult.reason));
            }

            if (campaignsResult.status === "fulfilled") {
                nextSnapshot.campaignTotal = campaignsResult.value.total;
                successfulSections += 1;
            } else {
                nextWarnings.push(buildSectionWarning("Marketing campaign", campaignsResult.reason));
            }

            if (activityResult.status === "fulfilled") {
                nextSnapshot.recentActivity = activityResult.value.items ?? [];
                successfulSections += 1;
            } else {
                nextWarnings.push(buildSectionWarning("Activity feed", activityResult.reason));
            }

            if (successfulSections === 0) {
                setSnapshot(EMPTY_SNAPSHOT);
                setWarnings([]);
                setErrorMessage("The dashboard overview could not be loaded from the backend.");
                return;
            }

            setSnapshot(nextSnapshot);
            setWarnings(nextWarnings);
        } catch (error) {
            console.error("Failed to load dashboard overview:", error);
            setSnapshot(EMPTY_SNAPSHOT);
            setWarnings([]);
            setErrorMessage(getApiErrorMessage(error, "The dashboard overview could not be loaded from the backend."));
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        void loadDashboard();
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, loadDashboard]);

    const cards = useMemo<DashboardCard[]>(() => {
        const nextCards: DashboardCard[] = [];

        if (snapshot.contactsTotal !== null) {
            nextCards.push({
                title: "Contacts",
                value: formatCount(snapshot.contactsTotal),
                description: snapshot.companiesTotal !== null
                    ? `${formatCount(snapshot.companiesTotal)} companies active in CRM.`
                    : "Customer relationships tracked in CRM.",
                href: "/contacts",
            });
        }

        if (snapshot.dealsTotal !== null || snapshot.salesReport) {
            nextCards.push({
                title: "Tracked Deals",
                value: snapshot.dealsTotal !== null ? formatCount(snapshot.dealsTotal) : "Unavailable",
                description: snapshot.salesReport
                    ? `${snapshot.salesReport.summary.overdue_follow_up_count} overdue follow-ups, ${snapshot.salesReport.summary.due_today_follow_up_count} due today.`
                    : "Monitor active pipeline and follow-up discipline.",
                href: "/sales/pipeline",
            });
        }

        if (snapshot.salesReport) {
            nextCards.push({
                title: "Weighted Pipeline",
                value: snapshot.salesReport.summary.currencies.length === 1
                    ? formatMoney(
                        snapshot.salesReport.summary.weighted_pipeline_amount,
                        snapshot.salesReport.summary.currencies[0],
                    )
                    : formatMixedCurrencySummary(snapshot.salesReport.summary.currencies),
                description: `Won this period: ${formatCount(snapshot.salesReport.summary.deals_won_this_period_count)} deals.`,
                href: "/reports/sales",
            });
        }

        if (snapshot.supportSummary) {
            nextCards.push({
                title: "Support Queue",
                value: formatCount(snapshot.supportSummary.open_count),
                description: `${formatCount(snapshot.supportSummary.urgent_count)} urgent, ${formatCount(snapshot.supportSummary.in_progress_count)} in progress.`,
                href: "/support",
            });
        }

        if (snapshot.financeSnapshot) {
            nextCards.push({
                title: "Open Receivables",
                value: snapshot.financeSnapshot.financial_statements.receivables.currencies.length === 1
                    ? formatMoney(
                        snapshot.financeSnapshot.financial_statements.receivables.open_receivables_amount,
                        snapshot.financeSnapshot.financial_statements.receivables.currencies[0],
                    )
                    : formatMixedCurrencySummary(snapshot.financeSnapshot.financial_statements.receivables.currencies),
                description: `${formatCount(snapshot.financeSnapshot.payments_summary.completed_payment_count)} completed payments recorded.`,
                href: "/reports/finance",
            });
        }

        if (snapshot.campaignTotal !== null) {
            nextCards.push({
                title: "Campaign Drafts",
                value: formatCount(snapshot.campaignTotal),
                description: "Email and WhatsApp drafts stored in Marketing.",
                href: "/marketing/campaigns",
            });
        }

        return nextCards;
    }, [snapshot]);

    const attentionItems = useMemo(() => {
        const items: Array<{ title: string; body: string; href: string }> = [];

        if (snapshot.salesReport) {
            items.push({
                title: "Pipeline follow-up",
                body: snapshot.salesReport.summary.overdue_follow_up_count > 0
                    ? `${snapshot.salesReport.summary.overdue_follow_up_count} deals are overdue for follow-up.`
                    : `${snapshot.salesReport.summary.due_today_follow_up_count} deals need follow-up today.`,
                href: "/reports/sales",
            });
        }

        if (snapshot.financeSnapshot) {
            items.push({
                title: "Collections",
                body: snapshot.financeSnapshot.financial_statements.receivables.overdue_invoice_count > 0
                    ? `${snapshot.financeSnapshot.financial_statements.receivables.overdue_invoice_count} invoices are overdue.`
                    : `${snapshot.financeSnapshot.financial_statements.receivables.issued_invoice_count} issued invoices are open for collection.`,
                href: "/finance/payments",
            });
        }

        if (snapshot.supportSummary) {
            items.push({
                title: "Support response",
                body: snapshot.supportSummary.urgent_count > 0
                    ? `${snapshot.supportSummary.urgent_count} urgent tickets need operator attention.`
                    : `${snapshot.supportSummary.resolved_this_period_count} tickets resolved this period.`,
                href: "/support",
            });
        }

        if (snapshot.campaignTotal !== null) {
            items.push({
                title: "Marketing drafts",
                body: snapshot.campaignTotal > 0
                    ? `${snapshot.campaignTotal} campaign drafts are ready for refinement.`
                    : "No campaign drafts exist yet for this tenant.",
                href: "/marketing/campaigns",
            });
        }

        return items;
    }, [snapshot]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                            Dashboard
                        </p>
                        <h1 className="mt-2 text-3xl font-bold text-slate-900">Overview</h1>
                        <p className="mt-2 max-w-3xl text-sm text-slate-600">
                            Track the real operating picture across CRM, Sales, Finance, Support, and Marketing from one tenant-aware workspace.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/sales/leads/create"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Add Lead
                        </Link>
                        <Link
                            href="/support/create"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Create Ticket
                        </Link>
                        <Link
                            href="/finance/invoices/create"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Create Invoice
                        </Link>
                        <Link
                            href="/marketing/campaigns"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Campaign Drafts
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading dashboard</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching live overview data, KPI summaries, and recent activity from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load dashboard</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                    <button
                        type="button"
                        onClick={() => {
                            void loadDashboard();
                        }}
                        className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Retry
                    </button>
                </section>
            ) : (
                <>
                    {warnings.length > 0 ? (
                        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                            <h2 className="text-sm font-semibold text-amber-900">Partial dashboard access</h2>
                            <div className="mt-2 space-y-1 text-sm text-amber-900">
                                {warnings.map((warning) => (
                                    <p key={warning}>{warning}</p>
                                ))}
                            </div>
                        </section>
                    ) : null}

                    <section id="kpis" className="space-y-4">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <h2 className="text-2xl font-semibold text-slate-900">KPIs</h2>
                                <p className="mt-1 text-sm text-slate-600">
                                    Real tenant metrics pulled from the current CRM, Sales, Finance, Support, and Marketing modules.
                                </p>
                            </div>
                            <Link
                                href="/reports/sales"
                                className="text-sm font-medium text-slate-700 underline underline-offset-2"
                            >
                                Open reports
                            </Link>
                        </div>

                        {cards.length === 0 ? (
                            <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                                <h3 className="text-lg font-semibold text-slate-900">No KPI data available</h3>
                                <p className="mt-2 text-sm text-slate-600">
                                    This account does not currently have enough module access to build a useful dashboard overview.
                                </p>
                            </div>
                        ) : (
                            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                                {cards.map((card) => (
                                    <Link
                                        key={card.title}
                                        href={card.href}
                                        className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-slate-300 hover:shadow"
                                    >
                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                            {card.title}
                                        </p>
                                        <p className="mt-3 text-3xl font-bold text-slate-900">{card.value}</p>
                                        <p className="mt-2 text-sm text-slate-600">{card.description}</p>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-2xl font-semibold text-slate-900">Operator Focus</h2>
                                    <p className="mt-1 text-sm text-slate-600">
                                        The highest-signal next steps across the currently implemented product surface.
                                    </p>
                                </div>
                            </div>

                            {attentionItems.length === 0 ? (
                                <div className="mt-6 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                    No cross-module attention items are available yet for this tenant.
                                </div>
                            ) : (
                                <div className="mt-6 space-y-3">
                                    {attentionItems.map((item) => (
                                        <Link
                                            key={item.title}
                                            href={item.href}
                                            className="block rounded-lg border border-slate-200 px-4 py-4 transition hover:border-slate-300 hover:bg-slate-50"
                                        >
                                            <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                                            <p className="mt-1 text-sm text-slate-600">{item.body}</p>
                                        </Link>
                                    ))}
                                </div>
                            )}
                        </div>

                        <section id="activity-feed" className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-2xl font-semibold text-slate-900">Activity Feed</h2>
                                    <p className="mt-1 text-sm text-slate-600">
                                        Recent tenant activity grounded in the current audit log stream.
                                    </p>
                                </div>
                            </div>

                            {snapshot.recentActivity.length === 0 ? (
                                <div className="mt-6 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                    No recent activity has been recorded for this tenant yet.
                                </div>
                            ) : (
                                <div className="mt-6 space-y-4">
                                    {snapshot.recentActivity.map((item) => {
                                        const actorLabel = item.actor_full_name || item.actor_email || "System";
                                        const statusTone = item.status_code !== null && item.status_code >= 400
                                            ? "text-amber-700"
                                            : "text-emerald-700";

                                        return (
                                            <article
                                                key={item.id}
                                                className="rounded-lg border border-slate-200 px-4 py-4"
                                            >
                                                <div className="flex items-start justify-between gap-4">
                                                    <div>
                                                        <p className="text-sm font-semibold text-slate-900">
                                                            {item.message?.trim() || formatActionLabel(item.action)}
                                                        </p>
                                                        <p className="mt-1 text-xs text-slate-500">
                                                            {formatActionLabel(item.action)}
                                                            {item.resource ? ` · ${formatActionLabel(item.resource)}` : ""}
                                                        </p>
                                                    </div>
                                                    <div className={`text-xs font-medium ${statusTone}`}>
                                                        {item.status_code ?? "ok"}
                                                    </div>
                                                </div>

                                                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
                                                    <span>{actorLabel}</span>
                                                    <span>{formatDateTime(item.created_at)}</span>
                                                </div>
                                            </article>
                                        );
                                    })}
                                </div>
                            )}
                        </section>
                    </section>
                </>
            )}
        </main>
    );
}

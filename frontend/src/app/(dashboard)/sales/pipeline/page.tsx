"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/feedback/ToastProvider";
import { DEAL_STAGES, PIPELINE_STAGE_TRANSITIONS, formatDealLabel, suggestStatusForStage } from "@/lib/deals";
import { getApiErrorMessage } from "@/lib/api-errors";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals, getPipelineReport, updateDeal } from "@/services/deals.service";
import type { Company, Contact, Deal, DealStage, PipelineStageCount } from "@/types/crm";

type PipelineSnapshot = {
    deals: Deal[];
    companies: Company[];
    contacts: Contact[];
    stageCounts: PipelineStageCount[];
    total: number;
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
        return "No contact";
    }

    const contact = contacts.find((item) => item.id === contactId);
    if (!contact) {
        return contactId;
    }

    return [contact.first_name, contact.last_name].filter(Boolean).join(" ");
}

async function loadPipelineSnapshot(): Promise<PipelineSnapshot> {
    const [dealsResponse, companiesResponse, contactsResponse, reportResponse] =
        await Promise.all([
            getDeals({ limit: 200, offset: 0 }),
            getCompanies(),
            getContacts(),
            getPipelineReport(),
        ]);

    return {
        deals: dealsResponse.items ?? [],
        companies: companiesResponse.items ?? [],
        contacts: contactsResponse.items ?? [],
        stageCounts: reportResponse.items ?? [],
        total: dealsResponse.total ?? 0,
    };
}

export default function SalesPipelinePage() {
    const toast = useToast();
    const [snapshot, setSnapshot] = useState<PipelineSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [updatingByDealId, setUpdatingByDealId] = useState<Record<string, boolean>>({});
    const [nextStageByDealId, setNextStageByDealId] = useState<Record<string, DealStage | "">>({});

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");
            const nextSnapshot = await loadPipelineSnapshot();
            setSnapshot(nextSnapshot);
        } catch (error) {
            console.error("Failed to load sales pipeline:", error);
            setErrorMessage(
                getApiErrorMessage(error, "The sales pipeline could not be loaded from the backend."),
            );
            setSnapshot(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadSnapshot();
    }, [loadSnapshot]);

    const countsByStage = useMemo(() => {
        const counts = new Map<DealStage, number>();
        snapshot?.stageCounts.forEach((item) => {
            counts.set(item.stage, item.count);
        });
        return counts;
    }, [snapshot]);

    const dealsByStage = useMemo(() => {
        const nextMap = new Map<DealStage, Deal[]>();
        DEAL_STAGES.forEach((stage) => {
            nextMap.set(stage, []);
        });

        snapshot?.deals.forEach((deal) => {
            const current = nextMap.get(deal.stage);
            if (current) {
                current.push(deal);
            }
        });

        return nextMap;
    }, [snapshot]);

    async function handleStageMove(deal: Deal): Promise<void> {
        const nextStage = nextStageByDealId[deal.id];
        if (!nextStage) {
            return;
        }

        try {
            setSuccessMessage("");
            setUpdatingByDealId((current) => ({
                ...current,
                [deal.id]: true,
            }));

            await updateDeal(deal.id, {
                stage: nextStage,
                status: suggestStatusForStage(nextStage, deal.status),
            });

            const message = `${deal.name} moved to ${formatDealLabel(nextStage)}.`;
            setSuccessMessage(message);
            toast.success(message);
            setNextStageByDealId((current) => ({
                ...current,
                [deal.id]: "",
            }));
            await loadSnapshot();
        } catch (error) {
            console.error("Failed to move deal in pipeline:", error);
            const message = getApiErrorMessage(error, "The deal could not be moved to the selected stage.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setUpdatingByDealId((current) => ({
                ...current,
                [deal.id]: false,
            }));
        }
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Sales Pipeline</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Review every deal by stage, track live counts, and advance the pipeline using the existing sales lifecycle.
                </p>
                {snapshot && snapshot.total > snapshot.deals.length ? (
                    <p className="mt-3 text-sm text-amber-700">
                        Showing the first {snapshot.deals.length} of {snapshot.total} deals on the board.
                    </p>
                ) : null}
            </section>

            {successMessage ? (
                <section className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 shadow-sm">
                    {successMessage}
                </section>
            ) : null}

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading pipeline</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching staged deals, companies, contacts, and pipeline counts from the backend API.
                    </p>
                </section>
            ) : errorMessage && !snapshot ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load pipeline</h2>
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
            ) : snapshot && snapshot.total === 0 ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">No deals in the pipeline</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Create a deal or add a lead before managing pipeline stages.
                    </p>
                </section>
            ) : snapshot ? (
                <>
                    {errorMessage ? (
                        <section className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-sm">
                            {errorMessage}
                        </section>
                    ) : null}

                    <section className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3">
                        {DEAL_STAGES.map((stage) => {
                            const stageDeals = dealsByStage.get(stage) ?? [];

                            return (
                                <section
                                    key={stage}
                                    className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                                >
                                    <div className="flex items-center justify-between gap-3">
                                        <div>
                                            <h2 className="text-lg font-semibold text-slate-900">
                                                {formatDealLabel(stage)}
                                            </h2>
                                            <p className="mt-1 text-sm text-slate-600">
                                                {countsByStage.get(stage) ?? 0} deal
                                                {(countsByStage.get(stage) ?? 0) === 1 ? "" : "s"}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="mt-4 space-y-3">
                                        {stageDeals.length === 0 ? (
                                            <div className="rounded-lg border border-dashed border-slate-200 px-4 py-5 text-sm text-slate-500">
                                                No deals currently sit in this stage.
                                            </div>
                                        ) : (
                                            stageDeals.map((deal) => {
                                                const availableTransitions =
                                                    PIPELINE_STAGE_TRANSITIONS[deal.stage] ?? [];
                                                const selectedNextStage = nextStageByDealId[deal.id] ?? "";

                                                return (
                                                    <article
                                                        key={deal.id}
                                                        className="rounded-lg border border-slate-200 p-4"
                                                    >
                                                        <div className="flex items-start justify-between gap-3">
                                                            <div>
                                                                <h3 className="text-sm font-semibold text-slate-900">
                                                                    {deal.name}
                                                                </h3>
                                                                <p className="mt-1 text-sm text-slate-600">
                                                                    {getCompanyName(snapshot.companies, deal.company_id)}
                                                                </p>
                                                                <p className="mt-1 text-xs text-slate-500">
                                                                    {getContactName(snapshot.contacts, deal.contact_id)}
                                                                </p>
                                                            </div>
                                                            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                                                                {formatDealLabel(deal.status)}
                                                            </span>
                                                        </div>

                                                        <div className="mt-4 flex items-center justify-between gap-3">
                                                            <span className="text-sm font-medium text-slate-900">
                                                                {formatMoney(deal.amount, deal.currency)}
                                                            </span>
                                                            <span className="text-xs text-slate-500">
                                                                {formatDealLabel(deal.stage)}
                                                            </span>
                                                        </div>

                                                        {availableTransitions.length > 0 ? (
                                                            <div className="mt-4 flex flex-col gap-2">
                                                                <label
                                                                    className="text-xs font-medium uppercase tracking-wide text-slate-500"
                                                                    htmlFor={`next-stage-${deal.id}`}
                                                                >
                                                                    Move stage
                                                                </label>
                                                                <div className="flex gap-2">
                                                                    <select
                                                                        id={`next-stage-${deal.id}`}
                                                                        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                                                        value={selectedNextStage}
                                                                        onChange={(event) =>
                                                                            setNextStageByDealId((current) => ({
                                                                                ...current,
                                                                                [deal.id]: event.target.value as DealStage,
                                                                            }))
                                                                        }
                                                                    >
                                                                        <option value="">Select next stage</option>
                                                                        {availableTransitions.map((nextStage) => (
                                                                            <option key={nextStage} value={nextStage}>
                                                                                {formatDealLabel(nextStage)}
                                                                            </option>
                                                                        ))}
                                                                    </select>
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => {
                                                                            void handleStageMove(deal);
                                                                        }}
                                                                        disabled={!selectedNextStage || Boolean(updatingByDealId[deal.id])}
                                                                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                                                    >
                                                                        {updatingByDealId[deal.id] ? "Updating..." : "Move"}
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <p className="mt-4 text-xs text-slate-500">
                                                                This is a terminal stage for the current lifecycle.
                                                            </p>
                                                        )}
                                                    </article>
                                                );
                                            })
                                        )}
                                    </div>
                                </section>
                            );
                        })}
                    </section>
                </>
            ) : null}
        </main>
    );
}

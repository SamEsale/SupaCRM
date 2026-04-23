"use client";

import { useEffect, useMemo, useState } from "react";

import { getDealFollowUpLabel, getDealFollowUpState, isActivePipelineStatus } from "@/lib/deals";
import { updateDealFollowUp } from "@/services/deals.service";
import type { Deal } from "@/types/crm";

type DealFollowUpCardProps = {
    deal: Deal;
    onUpdated?: (deal: Deal) => void;
};

function toDateTimeLocalValue(value: string | null): string {
    if (!value) {
        return "";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return "";
    }

    const year = parsed.getFullYear();
    const month = String(parsed.getMonth() + 1).padStart(2, "0");
    const day = String(parsed.getDate()).padStart(2, "0");
    const hours = String(parsed.getHours()).padStart(2, "0");
    const minutes = String(parsed.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function parseApiError(error: unknown): string {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
            return response.data.detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The follow-up could not be saved.";
}

function getStateClasses(state: ReturnType<typeof getDealFollowUpState>): string {
    if (state === "overdue") {
        return "bg-red-100 text-red-700";
    }
    if (state === "due-today") {
        return "bg-amber-100 text-amber-700";
    }
    if (state === "upcoming") {
        return "bg-blue-100 text-blue-700";
    }
    if (state === "closed") {
        return "bg-slate-100 text-slate-600";
    }
    return "bg-slate-100 text-slate-600";
}

export default function DealFollowUpCard({ deal, onUpdated }: DealFollowUpCardProps) {
    const [nextFollowUpAt, setNextFollowUpAt] = useState<string>(() => toDateTimeLocalValue(deal.next_follow_up_at));
    const [followUpNote, setFollowUpNote] = useState<string>(deal.follow_up_note ?? "");
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");

    useEffect(() => {
        setNextFollowUpAt(toDateTimeLocalValue(deal.next_follow_up_at));
        setFollowUpNote(deal.follow_up_note ?? "");
    }, [deal.follow_up_note, deal.next_follow_up_at, deal.id]);

    useEffect(() => {
        setErrorMessage("");
        setSuccessMessage("");
    }, [deal.id]);

    const followUpState = useMemo(() => getDealFollowUpState(deal), [deal]);
    const isClosed = !isActivePipelineStatus(deal.status);

    async function handleSave(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();

        try {
            setIsSaving(true);
            setErrorMessage("");
            setSuccessMessage("");

            const updatedDeal = await updateDealFollowUp(deal.id, {
                next_follow_up_at: nextFollowUpAt ? new Date(nextFollowUpAt).toISOString() : null,
                follow_up_note: followUpNote.trim() || null,
            });

            setSuccessMessage("Follow-up updated.");
            onUpdated?.(updatedDeal);
        } catch (error) {
            console.error("Failed to update deal follow-up:", error);
            setErrorMessage(parseApiError(error));
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 className="text-xl font-semibold text-slate-900">Follow-up workflow</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Keep the next touchpoint tied directly to this deal without leaving the sales workflow.
                    </p>
                </div>
                <span
                    className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${getStateClasses(followUpState)}`}
                >
                    {getDealFollowUpLabel(deal)}
                </span>
            </div>

            {isClosed ? (
                <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <p className="text-sm text-slate-600">
                        This deal is currently closed, so follow-up tracking is informational only until it is reopened.
                    </p>
                </div>
            ) : null}

            <form className="mt-6 space-y-4" onSubmit={handleSave}>
                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-follow-up-at">
                            Next follow-up
                        </label>
                        <input
                            id="deal-follow-up-at"
                            type="datetime-local"
                            value={nextFollowUpAt}
                            onChange={(event) => setNextFollowUpAt(event.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-follow-up-note">
                            Follow-up note
                        </label>
                        <textarea
                            id="deal-follow-up-note"
                            value={followUpNote}
                            onChange={(event) => setFollowUpNote(event.target.value)}
                            className="min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="Capture the next action, context, or promise made to the customer."
                        />
                    </div>
                </div>

                {errorMessage ? <p className="text-sm text-red-600">{errorMessage}</p> : null}
                {successMessage ? <p className="text-sm text-green-700">{successMessage}</p> : null}

                <div className="flex flex-wrap items-center gap-3">
                    <button
                        type="submit"
                        disabled={isSaving}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSaving ? "Saving..." : "Save follow-up"}
                    </button>
                    <button
                        type="button"
                        disabled={isSaving}
                        onClick={() => {
                            setNextFollowUpAt("");
                            setFollowUpNote("");
                            setErrorMessage("");
                            setSuccessMessage("");
                        }}
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        Clear fields
                    </button>
                </div>
            </form>
        </section>
    );
}

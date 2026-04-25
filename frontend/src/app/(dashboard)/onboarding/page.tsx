"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
    createTenantUser,
    getTenantOnboardingSummary,
    startCommercialSubscription,
    updateTenantStatus,
} from "@/services/tenants.service";
import { summarizeLaunchPackaging } from "@/components/onboarding/launch-packaging";
import { summarizeOnboardingState } from "@/components/onboarding/onboarding-utils";
import type { TenantOnboardingSummary, TenantStatus, TenantUserProvisionRequest } from "@/types/tenants";

const initialUserForm: TenantUserProvisionRequest = {
    email: "",
    full_name: "",
    password: "",
    role_names: ["admin"],
    is_owner: true,
};

function getScopedErrorMessage(error: unknown, fallback: string): string {
    const response = error as {
        response?: {
            data?: {
                detail?: unknown;
            };
        };
    };

    if (
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof response.response === "object" &&
        response.response !== null &&
        "data" in response.response &&
        typeof response.response.data === "object" &&
        response.response.data !== null &&
        "detail" in response.response.data &&
        typeof response.response.data.detail === "string" &&
        response.response.data.detail.trim().length > 0
    ) {
        return response.response.data.detail;
    }

    if (error instanceof Error && !/^Request failed with status code \d+$/i.test(error.message)) {
        return error.message;
    }

    return fallback;
}

export default function OnboardingPage() {
    const [summary, setSummary] = useState<TenantOnboardingSummary | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [summaryError, setSummaryError] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [userForm, setUserForm] = useState<TenantUserProvisionRequest>(initialUserForm);
    const [isSubmittingUser, setIsSubmittingUser] = useState<boolean>(false);
    const [isSubmittingCommercial, setIsSubmittingCommercial] = useState<boolean>(false);
    const [statusReason, setStatusReason] = useState<string>("");
    const [isSubmittingStatus, setIsSubmittingStatus] = useState<boolean>(false);
    const [userErrorMessage, setUserErrorMessage] = useState<string>("");
    const [commercialErrorMessage, setCommercialErrorMessage] = useState<string>("");
    const [statusErrorMessage, setStatusErrorMessage] = useState<string>("");

    async function loadSummary(): Promise<void> {
        setIsLoading(true);
        setSummaryError("");
        try {
            const data = await getTenantOnboardingSummary();
            setSummary(data);
        } catch (err) {
            setSummaryError(getScopedErrorMessage(err, "Failed to load onboarding state."));
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        void loadSummary();
    }, []);

    function resetFeedback(): void {
        setSuccessMessage("");
        setUserErrorMessage("");
        setCommercialErrorMessage("");
        setStatusErrorMessage("");
    }

    async function handleCreateUser(e: React.FormEvent<HTMLFormElement>): Promise<void> {
        e.preventDefault();
        resetFeedback();
        setIsSubmittingUser(true);
        try {
            await createTenantUser({
                ...userForm,
                email: userForm.email.trim(),
                full_name: userForm.full_name?.trim() || null,
                password: userForm.password?.trim() || null,
                role_names: userForm.role_names,
                is_owner: userForm.is_owner,
            });
            setSuccessMessage("Admin user created.");
            setUserErrorMessage("");
            setUserForm(initialUserForm);
            await loadSummary();
        } catch (err) {
            setUserErrorMessage(getScopedErrorMessage(err, "Failed to create admin user."));
        } finally {
            setIsSubmittingUser(false);
        }
    }

    async function handleStartTrial(): Promise<void> {
        resetFeedback();
        setIsSubmittingCommercial(true);
        try {
            await startCommercialSubscription({
                plan_code: "starter",
                provider: "stripe",
                start_trial: true,
                customer_email: undefined,
                customer_name: undefined,
            });
            setSuccessMessage("Commercial trial started.");
            setCommercialErrorMessage("");
            await loadSummary();
        } catch (err) {
            setCommercialErrorMessage(getScopedErrorMessage(err, "Failed to start subscription."));
        } finally {
            setIsSubmittingCommercial(false);
        }
    }

    async function handleUpdateTenantStatus(nextStatus: TenantStatus): Promise<void> {
        resetFeedback();
        setIsSubmittingStatus(true);
        try {
            await updateTenantStatus({
                status: nextStatus,
                status_reason: statusReason.trim() || null,
            });
            setSuccessMessage(`Tenant status updated to ${nextStatus}.`);
            setStatusErrorMessage("");
            await loadSummary();
        } catch (err) {
            setStatusErrorMessage(getScopedErrorMessage(err, "Failed to update tenant status."));
        } finally {
            setIsSubmittingStatus(false);
        }
    }

    const presentation = summarizeOnboardingState(summary);
    const launchPackaging = summarizeLaunchPackaging(summary?.commercial_subscription ?? null);

    return (
        <div className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                            Onboarding
                        </p>
                        <h1 className="mt-2 text-3xl font-bold text-slate-900">
                            {presentation.title}
                        </h1>
                        <p className="mt-2 max-w-2xl text-sm text-slate-600">
                            {presentation.description}
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={() => void loadSummary()}
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
                    >
                        Refresh
                    </button>
                </div>

                {isLoading ? (
                    <p className="mt-4 text-sm text-slate-500">Loading onboarding summary...</p>
                ) : null}
                {summaryError ? (
                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {summaryError}
                    </div>
                ) : null}
                {successMessage ? (
                    <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                        {successMessage}
                    </div>
                ) : null}
            </section>

            {summary ? (
                <>
                    <section className="grid gap-4 md:grid-cols-4">
                        <InfoCard label="Tenant status" value={summary.tenant.status} />
                        <InfoCard label="Commercial state" value={summary.commercial_subscription?.commercial_state ?? "missing"} />
                        <InfoCard label="Users" value={String(summary.users_total)} />
                        <InfoCard label="Owners" value={String(summary.owner_count)} />
                    </section>

                    <section className="grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
                        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <h2 className="text-lg font-semibold text-slate-900">Checklist</h2>
                            <div className="mt-4 space-y-3 text-sm">
                                <ChecklistRow
                                    label="First admin"
                                    passed={summary.owner_count > 0}
                                    detail={summary.owner_count > 0 ? "Owner/admin account exists." : "Create the first owner/admin."}
                                />
                                <ChecklistRow
                                    label="Commercial setup"
                                    passed={summary.bootstrap_complete && summary.ready_for_use}
                                    detail={summary.commercial_subscription ? `${summary.commercial_subscription.plan_code} · ${summary.commercial_subscription.commercial_state}` : "No commercial subscription yet."}
                                />
                                <ChecklistRow
                                    label="Tenant access"
                                    passed={summary.tenant.is_active}
                                    detail={summary.tenant.is_active ? "Tenant is active." : "Tenant needs activation."}
                                />
                            </div>

                            <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
                                <p className="text-sm font-semibold text-slate-900">{launchPackaging.title}</p>
                                <p className="mt-1 text-sm text-slate-600">{launchPackaging.description}</p>
                                <p className="mt-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                                    Tier
                                </p>
                                <p className="mt-1 text-sm text-slate-800">{launchPackaging.tierLabel}</p>

                                <div className="mt-4 grid gap-4 md:grid-cols-2">
                                    <div>
                                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                                            Included capabilities
                                        </p>
                                        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                                            {launchPackaging.includedCapabilities.length > 0 ? (
                                                launchPackaging.includedCapabilities.map((capability) => (
                                                    <li key={capability}>{capability}</li>
                                                ))
                                            ) : (
                                                <li>No packaged capabilities are defined yet.</li>
                                            )}
                                        </ul>
                                    </div>
                                    <div>
                                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                                            Launch limitations
                                        </p>
                                        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                                            {launchPackaging.launchLimitations.length > 0 ? (
                                                launchPackaging.launchLimitations.map((limitation) => (
                                                    <li key={limitation}>{limitation}</li>
                                                ))
                                            ) : (
                                                <li>No launch limitations documented.</li>
                                            )}
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {summary.missing_steps.length > 0 ? (
                                <div className="mt-5 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">
                                    <p className="font-semibold">Missing steps</p>
                                    <ul className="mt-2 list-disc space-y-1 pl-5">
                                        {summary.missing_steps.map((step) => (
                                            <li key={step}>{step.replaceAll("_", " ")}</li>
                                        ))}
                                    </ul>
                                </div>
                            ) : null}

                            {summary.warnings.length > 0 ? (
                                <div className="mt-4 rounded-lg bg-sky-50 p-4 text-sm text-sky-900">
                                    <p className="font-semibold">Warnings</p>
                                    <ul className="mt-2 list-disc space-y-1 pl-5">
                                        {summary.warnings.map((warning) => (
                                            <li key={warning}>{warning.replaceAll("_", " ")}</li>
                                        ))}
                                    </ul>
                                </div>
                            ) : null}
                        </div>

                        <div className="space-y-6">
                            <form onSubmit={handleCreateUser} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                                <h2 className="text-lg font-semibold text-slate-900">Create admin user</h2>
                                <p className="mt-1 text-sm text-slate-600">
                                    Add the first or next tenant operator without involving engineering. Ongoing user administration now lives in{" "}
                                    <Link href="/settings/users" className="font-medium text-slate-900 underline underline-offset-2">
                                        Settings / Users
                                    </Link>
                                    .
                                </p>

                                <div className="mt-4 space-y-3">
                                    <input
                                        value={userForm.email}
                                        onChange={(event) =>
                                            setUserForm((current) => ({ ...current, email: event.target.value }))
                                        }
                                        placeholder="Email"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        required
                                    />
                                    <input
                                        value={userForm.full_name ?? ""}
                                        onChange={(event) =>
                                            setUserForm((current) => ({
                                                ...current,
                                                full_name: event.target.value,
                                            }))
                                        }
                                        placeholder="Full name"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    />
                                    <input
                                        value={userForm.password ?? ""}
                                        onChange={(event) =>
                                            setUserForm((current) => ({
                                                ...current,
                                                password: event.target.value,
                                            }))
                                        }
                                        placeholder="Password"
                                        type="password"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    />
                                    <label className="flex items-center gap-2 text-sm text-slate-700">
                                        <input
                                            type="checkbox"
                                            checked={userForm.is_owner}
                                            onChange={(event) =>
                                                setUserForm((current) => ({
                                                    ...current,
                                                    is_owner: event.target.checked,
                                                }))
                                            }
                                        />
                                        Make this user an owner
                                    </label>
                                </div>

                                {userErrorMessage ? (
                                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                        {userErrorMessage}
                                    </div>
                                ) : null}

                                <button
                                    type="submit"
                                    disabled={isSubmittingUser}
                                    className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {isSubmittingUser ? "Creating..." : "Create user"}
                                </button>
                            </form>

                            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                                <h2 className="text-lg font-semibold text-slate-900">Commercial activation</h2>
                                <p className="mt-1 text-sm text-slate-600">
                                    Start or refresh the starter trial for this tenant.
                                </p>

                                <button
                                    type="button"
                                    disabled={isSubmittingCommercial}
                                    onClick={() => void handleStartTrial()}
                                    className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {isSubmittingCommercial ? "Starting..." : "Start starter trial"}
                                </button>

                                {commercialErrorMessage ? (
                                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                        {commercialErrorMessage}
                                    </div>
                                ) : null}
                            </div>

                            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                                <h2 className="text-lg font-semibold text-slate-900">Tenant access</h2>
                                <p className="mt-1 text-sm text-slate-600">
                                    Update tenant access state for onboarding or recovery.
                                </p>

                                <input
                                    value={statusReason}
                                    onChange={(event) => setStatusReason(event.target.value)}
                                    placeholder="Reason (optional)"
                                    className="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                />

                                <div className="mt-4 flex flex-wrap gap-3">
                                    <button
                                        type="button"
                                        disabled={isSubmittingStatus}
                                        onClick={() => void handleUpdateTenantStatus("active")}
                                        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {isSubmittingStatus ? "Updating..." : "Set active"}
                                    </button>
                                    <button
                                        type="button"
                                        disabled={isSubmittingStatus}
                                        onClick={() => void handleUpdateTenantStatus("suspended")}
                                        className="rounded-lg border border-amber-300 px-4 py-2 text-sm font-medium text-amber-800 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        Suspend
                                    </button>
                                    <button
                                        type="button"
                                        disabled={isSubmittingStatus}
                                        onClick={() => void handleUpdateTenantStatus("disabled")}
                                        className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        Disable
                                    </button>
                                </div>

                                {statusErrorMessage ? (
                                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                        {statusErrorMessage}
                                    </div>
                                ) : null}
                            </div>
                        </div>
                    </section>
                </>
            ) : null}
        </div>
    );
}

function InfoCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</p>
            <p className="mt-2 text-lg font-semibold text-slate-900">{value}</p>
        </div>
    );
}

function ChecklistRow({
    label,
    passed,
    detail,
}: {
    label: string;
    passed: boolean;
    detail: string;
}) {
    return (
        <div className="flex items-start gap-3 rounded-lg border border-slate-200 px-4 py-3">
            <div
                className={`mt-0.5 h-3 w-3 rounded-full ${passed ? "bg-emerald-500" : "bg-amber-500"}`}
                aria-hidden="true"
            />
            <div>
                <p className="font-medium text-slate-900">{label}</p>
                <p className="text-slate-600">{detail}</p>
            </div>
        </div>
    );
}

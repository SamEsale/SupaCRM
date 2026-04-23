"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/feedback/ToastProvider";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-errors";
import {
    cancelCommercialSubscription,
    changeCommercialSubscriptionPlan,
    createCommercialPaymentMethodCheckoutSession,
    getCommercialPlans,
    getCommercialSubscriptionSummary,
    getTenantCommercialStatus,
    listCommercialPaymentMethods,
    startCommercialSubscription,
} from "@/services/commercial.service";
import { getPaymentProviderFoundation } from "@/services/payments.service";
import type {
    CommercialPaymentMethod,
    CommercialPlan,
    CommercialSubscription,
    CommercialSubscriptionSummary,
    TenantCommercialStatus,
} from "@/types/commercial";
import type { PaymentProviderFoundationSnapshot } from "@/types/payments";

type BillingNoticeTone = "amber" | "green" | "red" | "slate";

function formatLabel(value: string): string {
    return value
        .split("_")
        .join(" ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatMoney(amount: string, currency: string): string {
    const numeric = Number(amount);
    if (Number.isNaN(numeric)) {
        return `${amount} ${currency}`;
    }
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(numeric);
}

function formatDateTime(value: string | null): string {
    if (!value) {
        return "Not available";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }

    return parsed.toLocaleString("en-US");
}

function getBillingNoticeToneClasses(tone: BillingNoticeTone): string {
    if (tone === "green") {
        return "border-emerald-200 bg-emerald-50 text-emerald-900";
    }
    if (tone === "red") {
        return "border-red-200 bg-red-50 text-red-900";
    }
    if (tone === "amber") {
        return "border-amber-200 bg-amber-50 text-amber-900";
    }
    return "border-slate-200 bg-slate-50 text-slate-900";
}

function buildBillingNotice(
    subscription: CommercialSubscription | null,
    subscriptionStatus: string | null,
    defaultPaymentMethod: CommercialPaymentMethod | null,
): {
    title: string;
    detail: string;
    tone: BillingNoticeTone;
    ctaLabel: string | null;
} {
    const normalizedStatus = subscriptionStatus?.trim().toLowerCase() ?? null;
    const commercialState = subscription?.commercial_state ?? null;
    const paymentMethodLabel = defaultPaymentMethod ? "Update Payment Method" : "Add Payment Method";

    if (normalizedStatus === "past_due" || commercialState === "past_due") {
        return {
            title: defaultPaymentMethod ? "Past Due" : "Past Due And Payment Method Missing",
            detail: defaultPaymentMethod
                ? "Stripe has reported a failed payment. Update the default payment method, then confirm a later success webhook before treating the tenant as recovered."
                : "Stripe has reported a failed payment and no active default payment method is available. Capture a new payment method first, then confirm the next Stripe event.",
            tone: "red",
            ctaLabel: paymentMethodLabel,
        };
    }

    if (!defaultPaymentMethod) {
        return {
            title: "Payment Method Missing",
            detail: "The tenant has no active default payment method on record. Paid subscription start stays blocked until Stripe setup checkout captures one.",
            tone: "amber",
            ctaLabel: "Add Payment Method",
        };
    }

    if (normalizedStatus === "pending" || normalizedStatus === "incomplete" || normalizedStatus === "incomplete_expired" || commercialState === "pending") {
        return {
            title: "Pending",
            detail: "The commercial record is waiting for Stripe webhook confirmation. Do not treat the tenant as fully recovered until a later Stripe event moves the subscription forward.",
            tone: "amber",
            ctaLabel: null,
        };
    }

    if (normalizedStatus === "trialing" || normalizedStatus === "trial" || commercialState === "trial") {
        return {
            title: "Trialing",
            detail: "The tenant is in a Stripe-backed trial state. Converting the trial to paid is only wired when a default payment method is already present.",
            tone: "green",
            ctaLabel: null,
        };
    }

    if (normalizedStatus === "active" || commercialState === "active") {
        return {
            title: "Active",
            detail: "Stripe currently reports the tenant as active. The existing payment method can still be updated if recovery or card rotation is needed.",
            tone: "green",
            ctaLabel: null,
        };
    }

    if (normalizedStatus === "canceled" || normalizedStatus === "cancelled" || commercialState === "canceled") {
        return {
            title: "Canceled",
            detail: "The tenant subscription is canceled in Stripe. This page does not implement a restart flow, so use Stripe and a fresh commercial action path before treating billing as live again.",
            tone: "slate",
            ctaLabel: null,
        };
    }

    return {
        title: "Billing State Available",
        detail: "The current commercial record is loaded. Use the captured Stripe status and recent provider events below before making any billing decision.",
        tone: "slate",
        ctaLabel: null,
    };
}

export default function SubscriptionBillingPage() {
    const auth = useAuth();
    const toast = useToast();
    const [summary, setSummary] = useState<CommercialSubscriptionSummary | null>(null);
    const [commercialStatus, setCommercialStatus] = useState<TenantCommercialStatus | null>(null);
    const [plans, setPlans] = useState<CommercialPlan[]>([]);
    const [paymentMethods, setPaymentMethods] = useState<CommercialPaymentMethod[]>([]);
    const [foundationSnapshot, setFoundationSnapshot] = useState<PaymentProviderFoundationSnapshot | null>(null);
    const [selectedPlanCode, setSelectedPlanCode] = useState<string>("starter");
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [activeAction, setActiveAction] = useState<string>("");
    const [errorMessage, setErrorMessage] = useState<string>("");

    async function reloadWorkspace(): Promise<void> {
        const [
            nextSummary,
            nextPlans,
            nextFoundation,
            nextCommercialStatus,
            nextPaymentMethods,
        ] = await Promise.all([
            getCommercialSubscriptionSummary(),
            getCommercialPlans(),
            getPaymentProviderFoundation(),
            getTenantCommercialStatus(),
            listCommercialPaymentMethods(),
        ]);

        setSummary(nextSummary);
        setCommercialStatus(nextCommercialStatus);
        setPlans(nextPlans);
        setFoundationSnapshot(nextFoundation);
        setPaymentMethods(nextPaymentMethods.items);
    }

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadWorkspace(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                await reloadWorkspace();
            } catch (error) {
                console.error("Failed to load subscription billing workspace:", error);
                if (isMounted) {
                    setErrorMessage(
                        getApiErrorMessage(error, "The subscription billing workspace could not be loaded."),
                    );
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadWorkspace();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    useEffect(() => {
        if (plans.length === 0) {
            return;
        }
        if (plans.some((plan) => plan.plan_code === selectedPlanCode)) {
            return;
        }
        setSelectedPlanCode(plans[0].plan_code);
    }, [plans, selectedPlanCode]);

    const subscription = summary?.subscription ?? commercialStatus?.subscription ?? null;
    const selectedPlan = useMemo(() => {
        if (selectedPlanCode) {
            const matched = plans.find((plan) => plan.plan_code === selectedPlanCode);
            if (matched) {
                return matched;
            }
        }
        if (commercialStatus?.current_plan) {
            return commercialStatus.current_plan;
        }
        return plans[0] ?? null;
    }, [commercialStatus?.current_plan, plans, selectedPlanCode]);
    const selectedPlanFoundation = useMemo(() => {
        if (!selectedPlan || !foundationSnapshot) {
            return null;
        }

        return foundationSnapshot.providers.find(
            (provider) => provider.provider === selectedPlan.provider,
        ) ?? null;
    }, [foundationSnapshot, selectedPlan]);
    const defaultPaymentMethod = useMemo(() => {
        return paymentMethods.find((method) => method.is_default) ?? paymentMethods[0] ?? null;
    }, [paymentMethods]);
    const subscriptionStatus = commercialStatus?.subscription_status ?? subscription?.subscription_status ?? null;
    const isTrialSubscription = Boolean(
        subscription
        && (
            subscription.commercial_state === "trial"
            || subscriptionStatus === "trial"
            || subscriptionStatus === "trialing"
        ),
    );
    const billingNotice = buildBillingNotice(subscription, subscriptionStatus, defaultPaymentMethod);
    const paymentMethodActionLabel = defaultPaymentMethod ? "Update Payment Method" : "Add Payment Method";

    const canStartTrial = Boolean(
        selectedPlan
        && selectedPlan.is_active
        && selectedPlan.trial_days > 0
        && !subscription,
    );
    const canStartSubscription = Boolean(
        selectedPlan
        && selectedPlan.is_active
        && selectedPlan.provider_price_id
        && defaultPaymentMethod
        && selectedPlanFoundation?.foundation_state === "ready"
        && selectedPlanFoundation.supports_automated_subscriptions
        && (!subscription || isTrialSubscription),
    );
    const canChangePlan = Boolean(
        subscription
        && subscription.provider_subscription_id
        && selectedPlan
        && selectedPlan.provider_price_id
        && selectedPlan.plan_code !== subscription.plan_code,
    );
    const canCancel = Boolean(
        subscription?.provider_subscription_id
        && !subscription.cancel_at_period_end,
    );

    async function runAction(actionName: string, callback: () => Promise<void>): Promise<void> {
        try {
            setActiveAction(actionName);
            setErrorMessage("");
            await callback();
            await reloadWorkspace();
        } catch (error) {
            console.error(`Failed to run billing action ${actionName}:`, error);
            const message = getApiErrorMessage(error, "Billing action failed.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setActiveAction("");
        }
    }

    async function handleStartSubscription(startTrial: boolean): Promise<void> {
        if (!selectedPlan) {
            return;
        }

        await runAction(startTrial ? "start_trial" : "start_subscription", async () => {
            await startCommercialSubscription({
                plan_code: selectedPlan.plan_code,
                provider: selectedPlan.provider,
                start_trial: startTrial,
                customer_email: auth.user?.email ?? undefined,
                customer_name: auth.user?.full_name ?? undefined,
            });
            toast.success(startTrial ? `${selectedPlan.name} trial started.` : `${selectedPlan.name} sent to Stripe.`);
        });
    }

    async function handleAddPaymentMethod(): Promise<void> {
        await runAction("add_payment_method", async () => {
            const session = await createCommercialPaymentMethodCheckoutSession({
                customer_email: auth.user?.email ?? undefined,
                customer_name: auth.user?.full_name ?? undefined,
            });
            window.location.assign(session.url);
        });
    }

    async function handleChangePlan(): Promise<void> {
        if (!selectedPlan) {
            return;
        }

        await runAction("change_plan", async () => {
            await changeCommercialSubscriptionPlan({
                new_plan_code: selectedPlan.plan_code,
                prorate: true,
            });
            toast.success(`${selectedPlan.name} change sent to Stripe.`);
        });
    }

    async function handleCancel(): Promise<void> {
        if (!subscription) {
            return;
        }

        await runAction("cancel_subscription", async () => {
            await cancelCommercialSubscription(subscription.id);
            toast.success("Cancellation requested with Stripe.");
        });
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                            Payments
                        </p>
                        <h1 className="mt-2 text-3xl font-bold text-slate-900">Subscription Billing</h1>
                        <p className="mt-2 max-w-3xl text-sm text-slate-600">
                            Stripe is the source of truth for subscription status. This page shows the tenant commercial record, payment-method readiness, and only the lifecycle actions that are actually wired.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/finance/payments/gateway-settings"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Gateway Settings
                        </Link>
                        <Link
                            href="/finance/payments/integrations"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Provider Foundation
                        </Link>
                    </div>
                </div>
            </section>

            {errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {errorMessage}
                </section>
            ) : null}

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading subscription billing</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching plan catalog, tenant commercial state, and Stripe-backed billing artifacts.
                    </p>
                </section>
            ) : null}

            {!isLoading && summary ? (
                <>
                    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                        <MetricCard
                            label="Current plan"
                            value={commercialStatus?.current_plan?.name ?? subscription?.plan_name ?? "Missing"}
                        />
                        <MetricCard
                            label="Subscription status"
                            value={subscriptionStatus ? formatLabel(subscriptionStatus) : "Missing"}
                        />
                        <MetricCard
                            label="Trial status"
                            value={formatLabel(commercialStatus?.trial_status ?? "not_applicable")}
                        />
                        <MetricCard
                            label="Renewal date"
                            value={formatDateTime(commercialStatus?.renewal_at ?? null)}
                        />
                        <MetricCard
                            label="Payment method"
                            value={defaultPaymentMethod ? "Present" : "Missing"}
                        />
                    </section>

                    <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <section className={`mb-5 rounded-xl border px-4 py-4 ${getBillingNoticeToneClasses(billingNotice.tone)}`}>
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div className="max-w-2xl">
                                        <p className="text-xs font-semibold uppercase tracking-[0.18em]">
                                            Recovery State
                                        </p>
                                        <h3 className="mt-2 text-lg font-semibold">{billingNotice.title}</h3>
                                        <p className="mt-2 text-sm opacity-90">{billingNotice.detail}</p>
                                    </div>
                                    {billingNotice.ctaLabel ? (
                                        <button
                                            type="button"
                                            disabled={activeAction !== ""}
                                            onClick={() => {
                                                void handleAddPaymentMethod();
                                            }}
                                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {activeAction === "add_payment_method" ? "Redirecting..." : billingNotice.ctaLabel}
                                        </button>
                                    ) : null}
                                </div>
                            </section>

                            <div className="flex flex-wrap items-center justify-between gap-3">
                                <h2 className="text-xl font-semibold text-slate-900">Billing controls</h2>
                                {plans.length > 0 ? (
                                    <select
                                        value={selectedPlan?.plan_code ?? ""}
                                        onChange={(event) => setSelectedPlanCode(event.target.value)}
                                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                    >
                                        {plans.map((plan) => (
                                            <option key={plan.plan_code} value={plan.plan_code}>
                                                {plan.name}
                                            </option>
                                        ))}
                                    </select>
                                ) : null}
                            </div>

                            {selectedPlan ? (
                                <>
                                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                                        <DetailCard
                                            label="Selected plan"
                                            value={`${selectedPlan.name} · ${formatMoney(selectedPlan.price_amount, selectedPlan.currency)}`}
                                        />
                                        <DetailCard
                                            label="Billing interval"
                                            value={formatLabel(selectedPlan.billing_interval)}
                                        />
                                        <DetailCard
                                            label="Provider"
                                            value={commercialStatus?.provider_name ?? formatLabel(selectedPlan.provider)}
                                        />
                                        <DetailCard
                                            label="Renewal"
                                            value={formatDateTime(commercialStatus?.renewal_at ?? null)}
                                        />
                                        <DetailCard
                                            label="Subscription record"
                                            value={subscription ? formatLabel(subscription.commercial_state) : "Missing"}
                                        />
                                        <DetailCard
                                            label="Payment method status"
                                            value={defaultPaymentMethod
                                                ? `${formatLabel(defaultPaymentMethod.card_brand ?? "card")} •••• ${defaultPaymentMethod.card_last4 ?? "0000"}`
                                                : "Payment Method Missing"}
                                        />
                                    </div>

                                    <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                                        <p className="text-sm font-medium text-slate-900">Provider foundation</p>
                                        <p className="mt-2 text-sm text-slate-600">
                                            {selectedPlanFoundation?.operator_summary ?? "No provider foundation summary is available yet."}
                                        </p>
                                        <p className="mt-2 text-xs text-slate-500">
                                            Foundation state: {formatLabel(selectedPlanFoundation?.foundation_state ?? "disabled")}
                                        </p>
                                    </div>

                                    <div className="mt-5 flex flex-wrap gap-3">
                                        <button
                                            type="button"
                                            disabled={activeAction !== ""}
                                            onClick={() => {
                                                void handleAddPaymentMethod();
                                            }}
                                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {activeAction === "add_payment_method" ? "Redirecting..." : paymentMethodActionLabel}
                                        </button>
                                        {!subscription || isTrialSubscription ? (
                                            <button
                                                type="button"
                                                disabled={!canStartSubscription || activeAction !== ""}
                                                onClick={() => {
                                                    void handleStartSubscription(false);
                                                }}
                                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                            >
                                                {activeAction === "start_subscription"
                                                    ? "Starting..."
                                                    : isTrialSubscription
                                                        ? "Convert Trial To Paid"
                                                        : "Start Subscription"}
                                            </button>
                                        ) : null}
                                        <button
                                            type="button"
                                            disabled={!canChangePlan || activeAction !== ""}
                                            onClick={() => {
                                                void handleChangePlan();
                                            }}
                                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {activeAction === "change_plan" ? "Changing..." : "Change Plan"}
                                        </button>
                                        <button
                                            type="button"
                                            disabled={!canCancel || activeAction !== ""}
                                            onClick={() => {
                                                void handleCancel();
                                            }}
                                            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {activeAction === "cancel_subscription" ? "Cancelling..." : "Cancel Subscription"}
                                        </button>
                                        {!subscription ? (
                                            <button
                                                type="button"
                                                disabled={!canStartTrial || activeAction !== ""}
                                                onClick={() => {
                                                    void handleStartSubscription(true);
                                                }}
                                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                            >
                                                {activeAction === "start_trial" ? "Starting..." : "Start Trial"}
                                            </button>
                                        ) : null}
                                    </div>

                                    {!defaultPaymentMethod ? (
                                        <p className="mt-3 text-sm text-amber-700">
                                            Stripe subscription start stays blocked until a tenant payment method has been captured.
                                        </p>
                                    ) : null}
                                    {subscription && !isTrialSubscription && !canStartSubscription ? (
                                        <p className="mt-3 text-sm text-slate-600">
                                            Paid subscription start is only wired for the first subscription or a trial-to-paid conversion. Recovery for existing paid states depends on Stripe events, not a local retry button.
                                        </p>
                                    ) : null}
                                    {subscription?.cancel_at_period_end ? (
                                        <p className="mt-3 text-sm text-slate-600">
                                            Cancellation is scheduled for the end of the current period.
                                        </p>
                                    ) : null}
                                </>
                            ) : (
                                <p className="mt-4 text-sm text-slate-600">
                                    No commercial plans are currently available.
                                </p>
                            )}
                        </section>

                        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Current subscription</h2>
                            {subscription ? (
                                <div className="mt-4 space-y-4">
                                    <DetailCard label="Current plan" value={subscription.plan_name} />
                                    <DetailCard
                                        label="Subscription status"
                                        value={subscriptionStatus ? formatLabel(subscriptionStatus) : "Missing"}
                                    />
                                    <DetailCard
                                        label="Trial status"
                                        value={formatLabel(commercialStatus?.trial_status ?? "not_applicable")}
                                    />
                                    <DetailCard
                                        label="Renewal date"
                                        value={formatDateTime(subscription.current_period_end_at)}
                                    />
                                    <DetailCard
                                        label="Payment method status"
                                        value={defaultPaymentMethod ? "Present" : "Payment Method Missing"}
                                    />
                                </div>
                            ) : (
                                <p className="mt-4 text-sm text-slate-600">
                                    No tenant subscription exists yet. Start with a plan or a trial to create the first commercial record.
                                </p>
                            )}
                        </section>
                    </section>

                    <section className="grid gap-6 xl:grid-cols-2">
                        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Recent billing cycles</h2>
                            {summary.recent_billing_cycles.length === 0 ? (
                                <p className="mt-4 text-sm text-slate-600">
                                    No billing cycles have been recorded yet.
                                </p>
                            ) : (
                                <div className="mt-4 overflow-x-auto">
                                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                                        <thead className="bg-slate-50">
                                            <tr className="text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                                                <th className="px-4 py-3">Cycle</th>
                                                <th className="px-4 py-3">Status</th>
                                                <th className="px-4 py-3">Amount</th>
                                                <th className="px-4 py-3">Due</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100">
                                            {summary.recent_billing_cycles.map((cycle) => (
                                                <tr key={cycle.id}>
                                                    <td className="px-4 py-3 text-slate-900">#{cycle.cycle_number}</td>
                                                    <td className="px-4 py-3 text-slate-700">{formatLabel(cycle.status)}</td>
                                                    <td className="px-4 py-3 text-slate-700">
                                                        {formatMoney(cycle.amount, cycle.currency)}
                                                    </td>
                                                    <td className="px-4 py-3 text-slate-700">{formatDateTime(cycle.due_at)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </section>

                        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Recent billing events</h2>
                            {summary.recent_billing_events.length === 0 ? (
                                <p className="mt-4 text-sm text-slate-600">
                                    No provider events have been recorded yet.
                                </p>
                            ) : (
                                <div className="mt-4 space-y-3">
                                    {summary.recent_billing_events.map((event) => (
                                        <article
                                            key={event.id}
                                            className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                                        >
                                            <div className="flex flex-wrap items-center justify-between gap-2">
                                                <p className="font-medium text-slate-900">
                                                    {event.event_type}
                                                </p>
                                                <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-700">
                                                    {formatLabel(event.processing_status)}
                                                </span>
                                            </div>
                                            <p className="mt-2 text-sm text-slate-600">
                                                {formatLabel(event.provider)} · {event.external_event_id}
                                            </p>
                                            <p className="mt-2 text-sm text-slate-600">
                                                Action: {event.action_taken ?? "No action recorded"}
                                            </p>
                                            {event.error_message ? (
                                                <p className="mt-2 text-sm text-red-700">{event.error_message}</p>
                                            ) : null}
                                            <p className="mt-2 text-xs text-slate-500">
                                                Created {formatDateTime(event.created_at)}
                                            </p>
                                        </article>
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

function MetricCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
            <p className="mt-3 text-2xl font-semibold text-slate-900">{value}</p>
        </div>
    );
}

function DetailCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
            <p className="mt-2 text-sm font-medium text-slate-900">{value}</p>
        </div>
    );
}

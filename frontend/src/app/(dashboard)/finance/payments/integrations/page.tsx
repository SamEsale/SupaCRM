"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-errors";
import { getCommercialSubscriptionSummary } from "@/services/commercial.service";
import { getPaymentProviderFoundation } from "@/services/payments.service";
import type { CommercialSubscriptionSummary } from "@/types/commercial";
import type { PaymentProviderFoundationSnapshot } from "@/types/payments";

function formatLabel(value: string): string {
    return value
        .split("_")
        .join(" ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function foundationTone(state: string): string {
    if (state === "ready") {
        return "border-emerald-200 bg-emerald-50";
    }
    if (state === "manual_only") {
        return "border-amber-200 bg-amber-50";
    }
    if (state === "needs_configuration") {
        return "border-blue-200 bg-blue-50";
    }
    return "border-slate-200 bg-slate-50";
}

export default function PaymentIntegrationsPage() {
    const auth = useAuth();
    const [foundationSnapshot, setFoundationSnapshot] = useState<PaymentProviderFoundationSnapshot | null>(null);
    const [subscriptionSummary, setSubscriptionSummary] = useState<CommercialSubscriptionSummary | null>(null);
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

        let isMounted = true;

        async function loadWorkspace(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                const [nextFoundation, nextSubscription] = await Promise.all([
                    getPaymentProviderFoundation(),
                    getCommercialSubscriptionSummary(),
                ]);

                if (!isMounted) {
                    return;
                }

                setFoundationSnapshot(nextFoundation);
                setSubscriptionSummary(nextSubscription);
            } catch (error) {
                console.error("Failed to load payment integrations workspace:", error);
                if (isMounted) {
                    setErrorMessage(
                        getApiErrorMessage(
                            error,
                            "The provider integration foundation could not be loaded.",
                        ),
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

    const activeSubscriptionProvider = useMemo(() => {
        return subscriptionSummary?.subscription?.provider ?? null;
    }, [subscriptionSummary]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                            Payments
                        </p>
                        <h1 className="mt-2 text-3xl font-bold text-slate-900">Provider Integrations</h1>
                        <p className="mt-2 max-w-3xl text-sm text-slate-600">
                            Review which providers are only stored as operator configuration, which ones can support commercial automation, and how the current tenant subscription maps onto that foundation.
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
                            href="/finance/payments/subscription-billing"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Subscription Billing
                        </Link>
                        <Link
                            href="/finance/payments"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Transactions
                        </Link>
                    </div>
                </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm text-slate-700">
                    This page does not imply live connectivity. It surfaces the product’s actual implementation state so operators can tell the difference between stored credentials, manual readiness, and real automated billing support.
                </p>
            </section>

            {errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {errorMessage}
                </section>
            ) : null}

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading provider foundation</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching provider capabilities and subscription context for the current tenant.
                    </p>
                </section>
            ) : null}

            {!isLoading && foundationSnapshot ? (
                <>
                    <section className="grid gap-4 md:grid-cols-3">
                        <MetricCard
                            label="Default provider"
                            value={
                                foundationSnapshot.default_provider
                                    ? formatLabel(foundationSnapshot.default_provider)
                                    : "Not selected"
                            }
                        />
                        <MetricCard
                            label="Automated providers"
                            value={String(
                                foundationSnapshot.providers.filter(
                                    (provider) => provider.supports_automated_subscriptions,
                                ).length,
                            )}
                        />
                        <MetricCard
                            label="Current subscription provider"
                            value={
                                activeSubscriptionProvider
                                    ? formatLabel(activeSubscriptionProvider)
                                    : "No subscription"
                            }
                        />
                    </section>

                    <section className="grid gap-4 xl:grid-cols-3">
                        {foundationSnapshot.providers.map((provider) => {
                            const isBackingSubscription = activeSubscriptionProvider === provider.provider;

                            return (
                                <article
                                    key={provider.provider}
                                    className={`rounded-xl border p-6 shadow-sm ${foundationTone(provider.foundation_state)}`}
                                >
                                    <div className="flex flex-wrap items-center gap-2">
                                        <h2 className="text-xl font-semibold text-slate-900">
                                            {provider.display_name}
                                        </h2>
                                        {provider.is_default ? (
                                            <span className="rounded-full bg-slate-900 px-2.5 py-1 text-xs font-medium text-white">
                                                Default
                                            </span>
                                        ) : null}
                                        {isBackingSubscription ? (
                                            <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-900">
                                                Current subscription
                                            </span>
                                        ) : null}
                                    </div>

                                    <p className="mt-3 text-sm text-slate-700">
                                        {provider.operator_summary}
                                    </p>

                                    <div className="mt-4 grid gap-2 text-sm text-slate-700">
                                        <CapabilityRow label="Foundation state" value={formatLabel(provider.foundation_state)} />
                                        <CapabilityRow label="Configured" value={formatLabel(provider.configuration_state)} />
                                        <CapabilityRow label="Enabled" value={provider.is_enabled ? "Yes" : "No"} />
                                        <CapabilityRow
                                            label="Checkout support"
                                            value={provider.supports_checkout_payments ? "Implemented" : "Not implemented"}
                                        />
                                        <CapabilityRow
                                            label="Webhooks"
                                            value={provider.supports_webhooks ? "Implemented" : "Not implemented"}
                                        />
                                        <CapabilityRow
                                            label="Subscription automation"
                                            value={provider.supports_automated_subscriptions ? "Implemented" : "Not implemented"}
                                        />
                                    </div>

                                    {provider.validation_errors.length > 0 ? (
                                        <div className="mt-4 rounded-lg border border-amber-200 bg-white/70 px-3 py-2 text-sm text-amber-900">
                                            {provider.validation_errors.join(" ")}
                                        </div>
                                    ) : null}
                                </article>
                            );
                        })}
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Operational read</h2>
                        <ul className="mt-4 space-y-2 text-sm text-slate-600">
                            <li>Stripe is the only provider in this slice that can move from saved tenant configuration into automated subscription billing.</li>
                            <li>Revolut Business and Payoneer are surfaced as operator-facing foundation only, so the UI avoids suggesting live subscription automation there.</li>
                            <li>Invoice-linked payment records remain separate from provider automation and continue to work through the existing finance flow.</li>
                        </ul>
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

function CapabilityRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex items-center justify-between gap-3 border-b border-black/5 pb-2 last:border-b-0 last:pb-0">
            <span className="text-slate-500">{label}</span>
            <span className="font-medium text-slate-900">{value}</span>
        </div>
    );
}

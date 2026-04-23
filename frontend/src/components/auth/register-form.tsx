"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import axios from "axios";

import { useToast } from "@/components/feedback/ToastProvider";
import { getApiErrorMessage } from "@/lib/api-errors";
import { setAuthStorage, setTenantId, setTokenStorage } from "@/lib/auth-storage";
import { getCurrentUser, register } from "@/services/auth.service";
import { getPublicCommercialCatalog } from "@/services/commercial.service";
import type { CommercialPlan } from "@/types/commercial";

interface RegisterFormState {
    companyName: string;
    fullName: string;
    email: string;
    password: string;
    planCode: string;
}

const initialState: RegisterFormState = {
    companyName: "",
    fullName: "",
    email: "",
    password: "",
    planCode: "",
};

function formatInterval(value: string): string {
    if (value === "year") {
        return "Yearly";
    }
    if (value === "month") {
        return "Monthly";
    }
    return value;
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

function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        return getApiErrorMessage(error, "Registration failed.");
    }
    if (error instanceof Error && error.message.trim()) {
        return error.message;
    }
    return "Registration failed.";
}

export default function RegisterForm() {
    const router = useRouter();
    const toast = useToast();
    const [form, setForm] = useState<RegisterFormState>(initialState);
    const [plans, setPlans] = useState<CommercialPlan[]>([]);
    const [isLoadingPlans, setIsLoadingPlans] = useState<boolean>(true);
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");

    useEffect(() => {
        let isMounted = true;

        async function loadPlans(): Promise<void> {
            try {
                const nextPlans = await getPublicCommercialCatalog();
                if (!isMounted) {
                    return;
                }
                setPlans(nextPlans);
                setForm((current) => ({
                    ...current,
                    planCode: current.planCode || nextPlans[0]?.plan_code || "",
                }));
            } catch (error) {
                if (isMounted) {
                    setErrorMessage(getErrorMessage(error));
                }
            } finally {
                if (isMounted) {
                    setIsLoadingPlans(false);
                }
            }
        }

        void loadPlans();
        return () => {
            isMounted = false;
        };
    }, []);

    const selectedPlan = plans.find((plan) => plan.plan_code === form.planCode) ?? null;

    function handleChange(event: React.ChangeEvent<HTMLInputElement>): void {
        const { name, value } = event.target;
        setForm((current) => ({
            ...current,
            [name]: value,
        }));
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();
        setErrorMessage("");
        setIsSubmitting(true);

        try {
            const response = await register({
                company_name: form.companyName,
                full_name: form.fullName || null,
                email: form.email,
                password: form.password,
                plan_code: form.planCode,
                provider: selectedPlan?.provider ?? "stripe",
                start_trial: true,
            });

            setTenantId(response.tenant_id);
            setTokenStorage(response.access_token, response.refresh_token);
            const currentUser = await getCurrentUser(response.tenant_id);
            setAuthStorage(response.access_token, response.refresh_token, currentUser);

            toast.success(`${response.tenant_name} is ready.`);
            router.push("/dashboard");
            router.refresh();
        } catch (error) {
            const message = getErrorMessage(error);
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="grid w-full max-w-6xl gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                    SupaCRM Plans
                </p>
                <h1 className="mt-3 text-4xl font-bold text-slate-900">Start with a real tenant and a real commercial record</h1>
                <p className="mt-3 max-w-2xl text-sm text-slate-600">
                    Choose a plan, create the first owner account, and start on the existing commercial foundation. This signup path starts with a grounded trial instead of a fake fully automated billing promise.
                </p>

                {isLoadingPlans ? (
                    <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                        Loading plan catalog...
                    </div>
                ) : (
                    <div className="mt-6 grid gap-4 md:grid-cols-2">
                        {plans.map((plan) => {
                            const isSelected = form.planCode === plan.plan_code;
                            return (
                                <button
                                    key={plan.plan_code}
                                    type="button"
                                    onClick={() => {
                                        setForm((current) => ({ ...current, planCode: plan.plan_code }));
                                    }}
                                    className={`rounded-2xl border p-5 text-left transition ${
                                        isSelected
                                            ? "border-slate-900 bg-slate-900 text-white"
                                            : "border-slate-200 bg-slate-50 text-slate-900 hover:border-slate-400"
                                    }`}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <h2 className="text-xl font-semibold">{plan.name}</h2>
                                            <p className={`mt-1 text-sm ${isSelected ? "text-slate-200" : "text-slate-600"}`}>
                                                {formatInterval(plan.billing_interval)}
                                            </p>
                                        </div>
                                        <p className="text-lg font-semibold">
                                            {formatMoney(plan.price_amount, plan.currency)}
                                        </p>
                                    </div>
                                    <ul className={`mt-4 space-y-2 text-sm ${isSelected ? "text-slate-100" : "text-slate-700"}`}>
                                        {plan.features_summary.length > 0 ? (
                                            plan.features_summary.map((item) => (
                                                <li key={item}>{item}</li>
                                            ))
                                        ) : (
                                            <li>Commercial packaging is configured on this plan.</li>
                                        )}
                                    </ul>
                                </button>
                            );
                        })}
                    </div>
                )}
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
                <h2 className="text-2xl font-bold text-slate-900">Create Workspace</h2>
                <p className="mt-2 text-sm text-slate-600">
                    The selected plan is attached during tenant bootstrap and the first owner is signed in immediately after registration.
                </p>

                <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
                    <div>
                        <label htmlFor="companyName" className="mb-1 block text-sm font-medium text-slate-700">
                            Company name
                        </label>
                        <input
                            id="companyName"
                            name="companyName"
                            type="text"
                            value={form.companyName}
                            onChange={handleChange}
                            required
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                        />
                    </div>

                    <div>
                        <label htmlFor="fullName" className="mb-1 block text-sm font-medium text-slate-700">
                            Your name
                        </label>
                        <input
                            id="fullName"
                            name="fullName"
                            type="text"
                            value={form.fullName}
                            onChange={handleChange}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                        />
                    </div>

                    <div>
                        <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
                            Work email
                        </label>
                        <input
                            id="email"
                            name="email"
                            type="email"
                            value={form.email}
                            onChange={handleChange}
                            required
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                        />
                    </div>

                    <div>
                        <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
                            Password
                        </label>
                        <input
                            id="password"
                            name="password"
                            type="password"
                            value={form.password}
                            onChange={handleChange}
                            required
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                        />
                    </div>

                    {selectedPlan ? (
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                            <p className="font-medium text-slate-900">
                                Selected plan: {selectedPlan.name}
                            </p>
                            <p className="mt-1">
                                Billing interval: {formatInterval(selectedPlan.billing_interval)}. Trial startup is enabled on this public path.
                            </p>
                        </div>
                    ) : null}

                    {errorMessage ? (
                        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                            {errorMessage}
                        </div>
                    ) : null}

                    <button
                        type="submit"
                        disabled={isSubmitting || !form.planCode || isLoadingPlans}
                        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? "Creating workspace..." : "Create workspace"}
                    </button>
                </form>

                <p className="mt-4 text-sm text-slate-600">
                    Already have an account?{" "}
                    <Link href="/login" className="font-medium text-slate-900 underline underline-offset-4">
                        Sign in
                    </Link>
                </p>
            </section>
        </div>
    );
}

"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-errors";
import {
    getMissingSecondaryCurrencyRateMessage,
    getSecondaryCurrencyDisplay,
} from "@/lib/finance-currency";
import {
    createExpense,
    getExpenses,
    updateExpense,
} from "@/services/expenses.service";
import { getCurrentTenant } from "@/services/tenants.service";
import type {
    Expense,
    ExpenseCreateRequest,
    ExpenseStatus,
} from "@/types/expenses";
import type { Tenant } from "@/types/tenants";

type ExpenseFormState = {
    title: string;
    description: string;
    amount: string;
    currency: string;
    expense_date: string;
    category: string;
    status: ExpenseStatus;
    vendor_name: string;
};

const DEFAULT_FORM_STATE: ExpenseFormState = {
    title: "",
    description: "",
    amount: "",
    currency: "USD",
    expense_date: "",
    category: "",
    status: "draft",
    vendor_name: "",
};

const STATUS_OPTIONS: ExpenseStatus[] = ["draft", "submitted", "approved", "paid"];

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

function formatDate(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleDateString("en-US");
}

function formatStatus(value: ExpenseStatus): string {
    return value
        .split("_")
        .join(" ")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function normalizeOptional(value: string): string | null {
    const normalized = value.trim();
    return normalized.length > 0 ? normalized : null;
}

function buildFormState(expense: Expense): ExpenseFormState {
    return {
        title: expense.title,
        description: expense.description ?? "",
        amount: expense.amount,
        currency: expense.currency,
        expense_date: expense.expense_date,
        category: expense.category,
        status: expense.status,
        vendor_name: expense.vendor_name ?? "",
    };
}

function validateForm(form: ExpenseFormState): string | null {
    if (!form.title.trim()) {
        return "Expense title is required.";
    }
    if (!form.category.trim()) {
        return "Expense category is required.";
    }

    const amount = Number(form.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
        return "Expense amount must be greater than zero.";
    }

    if (!/^[A-Z]{3}$/.test(form.currency.trim().toUpperCase())) {
        return "Expense currency must be a valid ISO 4217 3-letter code.";
    }

    if (!form.expense_date) {
        return "Expense date is required.";
    }

    return null;
}

export default function ExpensesPage() {
    const auth = useAuth();
    const [tenant, setTenant] = useState<Tenant | null>(null);
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [loadError, setLoadError] = useState<string>("");
    const [form, setForm] = useState<ExpenseFormState>(DEFAULT_FORM_STATE);
    const [editingExpenseId, setEditingExpenseId] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [saveError, setSaveError] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");

    const loadSnapshot = useCallback(async (): Promise<void> => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        try {
            setIsLoading(true);
            setLoadError("");

            const [tenantResponse, expensesResponse] = await Promise.all([
                getCurrentTenant(),
                getExpenses({ limit: 100, offset: 0 }),
            ]);

            setTenant(tenantResponse);
            setExpenses(expensesResponse.items ?? []);
            setForm((current) => ({
                ...current,
                currency:
                    current.title || current.amount || current.category || current.description || current.vendor_name || current.expense_date
                        ? current.currency
                        : tenantResponse.default_currency ?? "USD",
            }));
        } catch (error) {
            console.error("Failed to load expenses workspace:", error);
            setLoadError(getApiErrorMessage(error, "The expenses workspace could not be loaded from the backend."));
            setTenant(null);
            setExpenses([]);
        } finally {
            setIsLoading(false);
        }
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    useEffect(() => {
        void loadSnapshot();
    }, [loadSnapshot]);

    useEffect(() => {
        if (tenant?.default_currency && !editingExpenseId && !form.currency) {
            setForm((current) => ({
                ...current,
                currency: tenant.default_currency ?? "USD",
            }));
        }
    }, [editingExpenseId, form.currency, tenant?.default_currency]);

    const totalsByCurrency = useMemo(() => {
        const totals = new Map<string, number>();

        for (const expense of expenses) {
            const current = totals.get(expense.currency) ?? 0;
            totals.set(expense.currency, current + Number(expense.amount || "0"));
        }

        return Array.from(totals.entries()).map(([currency, total]) => ({
            currency,
            totalLabel: formatMoney(total.toFixed(2), currency),
        }));
    }, [expenses]);

    const submittedOrApprovedCount = useMemo(
        () => expenses.filter((expense) => expense.status === "submitted" || expense.status === "approved").length,
        [expenses],
    );

    const fxWorkspaceMessage = useMemo(() => {
        if (!tenant?.secondary_currency) {
            return null;
        }

        if (tenant.secondary_currency_rate) {
            return `Manual FX is active for ${tenant.default_currency} ↔ ${tenant.secondary_currency}. Converted values use the saved operator rate and timestamp from Company settings.`;
        }

        return `Secondary currency is configured for ${tenant.secondary_currency}, but no manual exchange rate has been saved yet.`;
    }, [tenant]);

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();
        setSaveError("");
        setSuccessMessage("");

        const validationError = validateForm(form);
        if (validationError) {
            setSaveError(validationError);
            return;
        }

        const payload: ExpenseCreateRequest = {
            title: form.title.trim(),
            description: normalizeOptional(form.description),
            amount: Number(form.amount),
            currency: form.currency.trim().toUpperCase(),
            expense_date: form.expense_date,
            category: form.category.trim(),
            status: form.status,
            vendor_name: normalizeOptional(form.vendor_name),
        };

        try {
            setIsSaving(true);

            if (editingExpenseId) {
                await updateExpense(editingExpenseId, payload);
                setSuccessMessage("Expense updated.");
            } else {
                await createExpense(payload);
                setSuccessMessage("Expense recorded.");
            }

            setEditingExpenseId(null);
            setForm({
                ...DEFAULT_FORM_STATE,
                currency: tenant?.default_currency ?? "USD",
            });
            await loadSnapshot();
        } catch (error) {
            console.error("Failed to save expense:", error);
            setSaveError(getApiErrorMessage(error, "The expense could not be saved."));
        } finally {
            setIsSaving(false);
        }
    }

    function startEditing(expense: Expense): void {
        setEditingExpenseId(expense.id);
        setSaveError("");
        setSuccessMessage("");
        setForm(buildFormState(expense));
    }

    function cancelEditing(): void {
        setEditingExpenseId(null);
        setSaveError("");
        setSuccessMessage("");
        setForm({
            ...DEFAULT_FORM_STATE,
            currency: tenant?.default_currency ?? "USD",
        });
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Expenses</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Record real operating expenses, move them through approval, and post accounting only when they are marked paid.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            href="/finance"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to Finance
                        </Link>
                        <Link
                            href="/finance/accounting"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Accounting
                        </Link>
                        <Link
                            href="/settings/company"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Manage FX settings
                        </Link>
                    </div>
                </div>

                {fxWorkspaceMessage ? (
                    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                        {fxWorkspaceMessage}
                    </div>
                ) : null}
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading expenses</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching tenant currency settings and expense records from the backend API.
                    </p>
                </section>
            ) : loadError ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load expenses</h2>
                    <p className="mt-2 text-sm text-slate-600">{loadError}</p>
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
            ) : (
                <>
                    <section className="grid gap-4 md:grid-cols-3">
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recorded expenses</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{expenses.length}</p>
                            <p className="mt-2 text-sm text-slate-600">All tenant-scoped expenses in the current workspace.</p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Awaiting finance action</p>
                            <p className="mt-3 text-3xl font-bold text-slate-900">{submittedOrApprovedCount}</p>
                            <p className="mt-2 text-sm text-slate-600">Submitted or approved expenses not yet marked paid.</p>
                        </article>
                        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Totals by currency</p>
                            <div className="mt-3 space-y-1 text-sm text-slate-900">
                                {totalsByCurrency.length === 0 ? (
                                    <p className="text-slate-600">No expenses recorded yet.</p>
                                ) : (
                                    totalsByCurrency.map((item) => (
                                        <p key={item.currency}>{item.totalLabel}</p>
                                    ))
                                )}
                            </div>
                        </article>
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h2 className="text-xl font-semibold text-slate-900">
                                    {editingExpenseId ? "Edit expense" : "Record expense"}
                                </h2>
                                <p className="mt-2 text-sm text-slate-600">
                                    Paid expenses become accounting-visible immediately. Draft, submitted, and approved expenses stay operational until you mark them paid.
                                </p>
                            </div>
                            {editingExpenseId ? (
                                <button
                                    type="button"
                                    onClick={cancelEditing}
                                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                >
                                    Cancel edit
                                </button>
                            ) : null}
                        </div>

                        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="expense-title">
                                        Title
                                    </label>
                                    <input
                                        id="expense-title"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.title}
                                        onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                                        placeholder="Meta ads"
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="expense-vendor">
                                        Vendor / company
                                    </label>
                                    <input
                                        id="expense-vendor"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.vendor_name}
                                        onChange={(event) => setForm((current) => ({ ...current, vendor_name: event.target.value }))}
                                        placeholder="Meta"
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="expense-amount">
                                        Amount
                                    </label>
                                    <input
                                        id="expense-amount"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.amount}
                                        onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
                                        placeholder="120.00"
                                        inputMode="decimal"
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="expense-currency">
                                        Currency
                                    </label>
                                    <input
                                        id="expense-currency"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                                        value={form.currency}
                                        onChange={(event) => setForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))}
                                        maxLength={3}
                                        placeholder={tenant?.default_currency ?? "USD"}
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="expense-date">
                                        Expense date
                                    </label>
                                    <input
                                        id="expense-date"
                                        type="date"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.expense_date}
                                        onChange={(event) => setForm((current) => ({ ...current, expense_date: event.target.value }))}
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="expense-category">
                                        Category
                                    </label>
                                    <input
                                        id="expense-category"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.category}
                                        onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
                                        placeholder="marketing"
                                    />
                                </div>
                                <div className="md:col-span-2">
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="expense-status">
                                        Status
                                    </label>
                                    <select
                                        id="expense-status"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.status}
                                        onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as ExpenseStatus }))}
                                    >
                                        {STATUS_OPTIONS.map((status) => (
                                            <option key={status} value={status}>
                                                {formatStatus(status)}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="md:col-span-2">
                                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="expense-description">
                                        Notes
                                    </label>
                                    <textarea
                                        id="expense-description"
                                        className="min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                        value={form.description}
                                        onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                                        placeholder="Campaign spend for April launch"
                                    />
                                </div>
                            </div>

                            {saveError ? (
                                <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                    {saveError}
                                </p>
                            ) : null}
                            {successMessage ? (
                                <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                                    {successMessage}
                                </p>
                            ) : null}

                            <div className="flex justify-end">
                                <button
                                    type="submit"
                                    disabled={isSaving}
                                    className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {isSaving ? "Saving..." : editingExpenseId ? "Save expense changes" : "Record expense"}
                                </button>
                            </div>
                        </form>
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Expense records</h2>
                        <div className="mt-6 space-y-3">
                            {expenses.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                    No expenses have been recorded yet.
                                </div>
                            ) : (
                                expenses.map((expense) => {
                                    const convertedAmount = getSecondaryCurrencyDisplay(tenant, expense.amount, expense.currency);
                                    const missingRateMessage = getMissingSecondaryCurrencyRateMessage(tenant, expense.currency);

                                    return (
                                        <article key={expense.id} className="rounded-lg border border-slate-200 px-4 py-4">
                                            <div className="flex flex-wrap items-start justify-between gap-4">
                                                <div>
                                                    <p className="font-medium text-slate-900">{expense.title}</p>
                                                    <p className="mt-1 text-sm text-slate-600">
                                                        {formatStatus(expense.status)} • {expense.category} • {formatDate(expense.expense_date)}
                                                    </p>
                                                    <p className="mt-1 text-sm text-slate-600">
                                                        {formatMoney(expense.amount, expense.currency)}
                                                        {expense.vendor_name ? ` • ${expense.vendor_name}` : ""}
                                                    </p>
                                                    {convertedAmount ? (
                                                        <p className="mt-1 text-xs text-slate-500">
                                                            {convertedAmount.convertedAmountLabel} • {convertedAmount.rateLabel} • {convertedAmount.sourceLabel} • {convertedAmount.asOfLabel}
                                                        </p>
                                                    ) : missingRateMessage ? (
                                                        <p className="mt-1 text-xs text-amber-700">{missingRateMessage}</p>
                                                    ) : null}
                                                    {expense.description ? (
                                                        <p className="mt-2 text-sm text-slate-600">{expense.description}</p>
                                                    ) : null}
                                                </div>

                                                <div className="flex flex-wrap gap-2">
                                                    {expense.status === "paid" ? (
                                                        <Link
                                                            href={`/finance/accounting?source_type=expense&source_id=${expense.id}`}
                                                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                                        >
                                                            View accounting
                                                        </Link>
                                                    ) : (
                                                        <button
                                                            type="button"
                                                            onClick={() => startEditing(expense)}
                                                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                                        >
                                                            Edit
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </article>
                                    );
                                })
                            )}
                        </div>
                    </section>
                </>
            )}
        </main>
    );
}

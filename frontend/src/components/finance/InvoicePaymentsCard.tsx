"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useToast } from "@/components/feedback/ToastProvider";
import {
    parseStrictDecimalAmountInput,
    sanitizeStrictDecimalInput,
    TOTAL_AMOUNT_INVALID_MESSAGE,
    shouldBlockStrictDecimalKey,
} from "@/components/finance/amount-utils";
import { getApiErrorMessage } from "@/lib/api-errors";
import { createPayment, getInvoicePaymentSummary, getPayments } from "@/services/payments.service";
import type { Invoice } from "@/types/finance";
import type { InvoicePayment, InvoicePaymentSummary, PaymentMethod } from "@/types/payments";

type InvoicePaymentsCardProps = {
    invoice: Invoice;
    onPaymentRecorded?: () => Promise<void> | void;
};

type PaymentFormState = {
    amount: string;
    payment_date: string;
    method: PaymentMethod;
    external_reference: string;
    notes: string;
};

type PaymentFormErrors = Partial<Record<"amount" | "payment_date" | "method", string>>;

const DEFAULT_METHOD: PaymentMethod = "bank_transfer";

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

function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

function formatMethod(value: string): string {
    return value
        .split("_")
        .join(" ")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function getDefaultPaymentDate(): string {
    const now = new Date();
    const offset = now.getTimezoneOffset();
    const local = new Date(now.getTime() - offset * 60_000);
    return local.toISOString().slice(0, 16);
}

function toApiDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toISOString();
}

function getAvailabilityMessage(invoice: Invoice, summary: InvoicePaymentSummary | null): string | null {
    if (invoice.status === "draft") {
        return "Issue the invoice before recording payments.";
    }
    if (invoice.status === "cancelled") {
        return "Cancelled invoices cannot accept payments.";
    }
    if (summary && Number(summary.outstanding_amount) <= 0) {
        return "This invoice is already fully paid.";
    }
    return null;
}

export default function InvoicePaymentsCard({
    invoice,
    onPaymentRecorded,
}: InvoicePaymentsCardProps) {
    const toast = useToast();
    const submitLockRef = useRef(false);
    const [payments, setPayments] = useState<InvoicePayment[]>([]);
    const [summary, setSummary] = useState<InvoicePaymentSummary | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [loadError, setLoadError] = useState<string>("");
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [submitError, setSubmitError] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [formErrors, setFormErrors] = useState<PaymentFormErrors>({});
    const [form, setForm] = useState<PaymentFormState>({
        amount: invoice.total_amount,
        payment_date: getDefaultPaymentDate(),
        method: DEFAULT_METHOD,
        external_reference: "",
        notes: "",
    });

    const loadSnapshot = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setLoadError("");
            const [paymentsResponse, summaryResponse] = await Promise.all([
                getPayments({ invoice_id: invoice.id, limit: 50, offset: 0 }),
                getInvoicePaymentSummary(invoice.id),
            ]);
            setPayments(paymentsResponse.items ?? []);
            setSummary(summaryResponse);
            setForm((current) => ({
                ...current,
                amount: summaryResponse.outstanding_amount,
            }));
        } catch (error) {
            console.error("Failed to load invoice payments:", error);
            setLoadError(getApiErrorMessage(error, "The invoice payments workspace could not be loaded from the backend."));
            setPayments([]);
            setSummary(null);
        } finally {
            setIsLoading(false);
        }
    }, [invoice.id]);

    useEffect(() => {
        setSuccessMessage("");
        void loadSnapshot();
    }, [loadSnapshot]);

    const availabilityMessage = useMemo(() => getAvailabilityMessage(invoice, summary), [invoice, summary]);

    function validateForm(): PaymentFormErrors {
        const nextErrors: PaymentFormErrors = {};
        const amountResult = parseStrictDecimalAmountInput(form.amount);

        if (amountResult.error) {
            nextErrors.amount = amountResult.error;
        }
        if (!form.payment_date) {
            nextErrors.payment_date = "Payment date and time is required.";
        }
        if (!form.method) {
            nextErrors.method = "Payment method is required.";
        }

        return nextErrors;
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();

        if (submitLockRef.current || isSubmitting || availabilityMessage) {
            return;
        }

        setSubmitError("");
        setSuccessMessage("");
        const nextErrors = validateForm();
        setFormErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0) {
            return;
        }

        const amountResult = parseStrictDecimalAmountInput(form.amount);
        if (amountResult.error || amountResult.value === null) {
            setFormErrors((current) => ({
                ...current,
                amount: amountResult.error ?? TOTAL_AMOUNT_INVALID_MESSAGE,
            }));
            return;
        }

        try {
            submitLockRef.current = true;
            setIsSubmitting(true);

            await createPayment({
                invoice_id: invoice.id,
                amount: amountResult.value,
                currency: invoice.currency,
                method: form.method,
                status: "completed",
                payment_date: toApiDateTime(form.payment_date),
                external_reference: form.external_reference.trim() || null,
                notes: form.notes.trim() || null,
            });

            const message = "Payment recorded successfully.";
            setSuccessMessage(message);
            toast.success(message);
            await loadSnapshot();
            if (onPaymentRecorded) {
                await onPaymentRecorded();
            }
        } catch (error) {
            console.error("Failed to record invoice payment:", error);
            const message = getApiErrorMessage(error, "Failed to record payment.");
            setSubmitError(message);
            toast.error(message);
        } finally {
            submitLockRef.current = false;
            setIsSubmitting(false);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Payments</h2>
            <p className="mt-2 text-sm text-slate-600">
                Record received invoice payments manually in this launch slice. No live gateway connection is implied here.
            </p>

            {isLoading ? (
                <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    Loading payment records and current payment state.
                </div>
            ) : loadError ? (
                <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
                    <p className="text-sm font-medium text-red-800">Failed to load payments</p>
                    <p className="mt-2 text-sm text-red-700">{loadError}</p>
                    <button
                        type="button"
                        onClick={() => {
                            void loadSnapshot();
                        }}
                        className="mt-3 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-100"
                    >
                        Retry
                    </button>
                </div>
            ) : (
                <>
                    {summary ? (
                        <div className="mt-6 grid gap-4 md:grid-cols-3">
                            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Payment state</p>
                                <p className="mt-2 text-xl font-semibold text-slate-900">{summary.payment_state}</p>
                                <p className="mt-2 text-sm text-slate-600">{summary.payment_count} recorded payment{summary.payment_count === 1 ? "" : "s"}.</p>
                            </article>
                            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Received</p>
                                <p className="mt-2 text-xl font-semibold text-slate-900">
                                    {formatMoney(summary.completed_amount, summary.currency)}
                                </p>
                                <p className="mt-2 text-sm text-slate-600">{summary.completed_payment_count} completed payment{summary.completed_payment_count === 1 ? "" : "s"}.</p>
                            </article>
                            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Outstanding</p>
                                <p className="mt-2 text-xl font-semibold text-slate-900">
                                    {formatMoney(summary.outstanding_amount, summary.currency)}
                                </p>
                                <p className="mt-2 text-sm text-slate-600">{summary.pending_payment_count} pending payment{summary.pending_payment_count === 1 ? "" : "s"}.</p>
                            </article>
                        </div>
                    ) : null}

                    <div className="mt-6 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                        <div>
                            <h3 className="text-lg font-semibold text-slate-900">Recorded payments</h3>
                            <div className="mt-4 space-y-3">
                                {payments.length === 0 ? (
                                    <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                        No payment records have been saved for this invoice yet.
                                    </div>
                                ) : (
                                    payments.map((payment) => (
                                        <div key={payment.id} className="rounded-lg border border-slate-200 px-4 py-4">
                                            <div className="flex flex-wrap items-start justify-between gap-4">
                                                <div>
                                                    <p className="font-medium text-slate-900">
                                                        {formatMethod(payment.method)} · {payment.status}
                                                    </p>
                                                    <p className="mt-1 text-sm text-slate-600">{formatDateTime(payment.payment_date)}</p>
                                                    {payment.external_reference ? (
                                                        <p className="mt-1 text-xs text-slate-500">
                                                            Ref: {payment.external_reference}
                                                        </p>
                                                    ) : null}
                                                </div>
                                                <p className="text-sm font-medium text-slate-900">
                                                    {formatMoney(payment.amount, payment.currency)}
                                                </p>
                                            </div>
                                            {payment.notes ? (
                                                <p className="mt-3 text-sm text-slate-600">{payment.notes}</p>
                                            ) : null}
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div>
                            <h3 className="text-lg font-semibold text-slate-900">Record payment</h3>
                            <p className="mt-2 text-sm text-slate-600">
                                Use this when payment has already been received outside of a live gateway flow.
                            </p>

                            {availabilityMessage ? (
                                <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                                    {availabilityMessage}
                                </div>
                            ) : (
                                <form className="mt-4 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="payment-amount">
                                            Amount
                                        </label>
                                        <input
                                            id="payment-amount"
                                            type="text"
                                            inputMode="decimal"
                                            value={form.amount}
                                            onChange={(event) => {
                                                setForm((current) => ({
                                                    ...current,
                                                    amount: sanitizeStrictDecimalInput(event.target.value),
                                                }));
                                                setFormErrors((current) => ({ ...current, amount: undefined }));
                                            }}
                                            onKeyDown={(event) => {
                                                if (shouldBlockStrictDecimalKey(event.key)) {
                                                    event.preventDefault();
                                                }
                                            }}
                                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                                            placeholder="0.00"
                                        />
                                        {formErrors.amount ? (
                                            <p className="mt-1 text-sm text-red-600">{formErrors.amount}</p>
                                        ) : null}
                                    </div>

                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="payment-date">
                                            Payment date and time
                                        </label>
                                        <input
                                            id="payment-date"
                                            type="datetime-local"
                                            value={form.payment_date}
                                            onChange={(event) => {
                                                setForm((current) => ({
                                                    ...current,
                                                    payment_date: event.target.value,
                                                }));
                                                setFormErrors((current) => ({ ...current, payment_date: undefined }));
                                            }}
                                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                                        />
                                        {formErrors.payment_date ? (
                                            <p className="mt-1 text-sm text-red-600">{formErrors.payment_date}</p>
                                        ) : null}
                                    </div>

                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="payment-method">
                                            Method
                                        </label>
                                        <select
                                            id="payment-method"
                                            value={form.method}
                                            onChange={(event) => {
                                                setForm((current) => ({
                                                    ...current,
                                                    method: event.target.value as PaymentMethod,
                                                }));
                                                setFormErrors((current) => ({ ...current, method: undefined }));
                                            }}
                                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                                        >
                                            <option value="bank_transfer">Bank transfer</option>
                                            <option value="cash">Cash</option>
                                            <option value="card_manual">Card manual</option>
                                            <option value="other">Other</option>
                                        </select>
                                        {formErrors.method ? (
                                            <p className="mt-1 text-sm text-red-600">{formErrors.method}</p>
                                        ) : null}
                                    </div>

                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="payment-reference">
                                            External reference
                                        </label>
                                        <input
                                            id="payment-reference"
                                            type="text"
                                            value={form.external_reference}
                                            onChange={(event) => {
                                                setForm((current) => ({
                                                    ...current,
                                                    external_reference: event.target.value,
                                                }));
                                            }}
                                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                                            placeholder="Bank transfer id, receipt number, or card reference"
                                        />
                                    </div>

                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="payment-notes">
                                            Notes
                                        </label>
                                        <textarea
                                            id="payment-notes"
                                            value={form.notes}
                                            onChange={(event) => {
                                                setForm((current) => ({
                                                    ...current,
                                                    notes: event.target.value,
                                                }));
                                            }}
                                            rows={4}
                                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                                            placeholder="Optional context about the received payment"
                                        />
                                    </div>

                                    {submitError ? (
                                        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                            {submitError}
                                        </div>
                                    ) : null}

                                    {successMessage ? (
                                        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                                            {successMessage}
                                        </div>
                                    ) : null}

                                    <button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {isSubmitting ? "Recording..." : "Record payment"}
                                    </button>
                                </form>
                            )}
                        </div>
                    </div>
                </>
            )}
        </section>
    );
}

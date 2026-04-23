"use client";

import { useEffect, useMemo, useState } from "react";

import {
    parseStrictDecimalAmountInput,
    sanitizeStrictDecimalInput,
    TOTAL_AMOUNT_INVALID_MESSAGE,
    shouldBlockStrictDecimalKey,
} from "@/components/finance/amount-utils";
import { DEAL_STAGES, DEAL_STATUSES, formatDealLabel } from "@/lib/deals";
import { createDeal } from "@/services/deals.service";
import type { Company, Contact, DealCreateRequest } from "@/types/crm";
import type { Product } from "@/types/product";

type DealFormMode = "create" | "edit";

type DealCreateFormProps = {
    companies: Company[];
    contacts: Contact[];
    products: Product[];
    onCreated?: () => Promise<void> | void;
    onSuccess?: () => Promise<void> | void;
    onSubmit?: (payload: DealCreateRequest) => Promise<void>;
    initialValues?: Partial<DealCreateRequest>;
    mode?: DealFormMode;
    title?: string;
    description?: string;
    submitLabel?: string;
    submittingLabel?: string;
    successMessage?: string;
};

const DEFAULT_FORM_STATE: DealCreateRequest = {
    name: "",
    company_id: "",
    contact_id: null,
    product_id: null,
    amount: "",
    currency: "USD",
    stage: "new lead",
    status: "open",
    expected_close_date: null,
    notes: null,
};

function buildInitialFormState(
    initialValues?: Partial<DealCreateRequest>,
): DealCreateRequest {
    return {
        ...DEFAULT_FORM_STATE,
        ...initialValues,
        name: initialValues?.name ?? DEFAULT_FORM_STATE.name,
        company_id: initialValues?.company_id ?? DEFAULT_FORM_STATE.company_id,
        contact_id: initialValues?.contact_id ?? DEFAULT_FORM_STATE.contact_id,
        product_id: initialValues?.product_id ?? DEFAULT_FORM_STATE.product_id,
        amount: initialValues?.amount ?? DEFAULT_FORM_STATE.amount,
        currency: initialValues?.currency ?? DEFAULT_FORM_STATE.currency,
        stage: initialValues?.stage ?? DEFAULT_FORM_STATE.stage,
        status: initialValues?.status ?? DEFAULT_FORM_STATE.status,
        expected_close_date:
            initialValues?.expected_close_date ?? DEFAULT_FORM_STATE.expected_close_date,
        notes: initialValues?.notes ?? DEFAULT_FORM_STATE.notes,
    };
}

function parseApiError(error: unknown): string {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
            return response.data.detail;
        }
    }
    return "The deal could not be saved.";
}

export default function DealCreateForm({
    companies,
    contacts,
    products,
    onCreated,
    onSuccess,
    onSubmit,
    initialValues,
    mode = "create",
    title,
    description,
    submitLabel,
    submittingLabel,
    successMessage,
}: DealCreateFormProps) {
    const [formData, setFormData] = useState<DealCreateRequest>(() =>
        buildInitialFormState(initialValues),
    );
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [amountError, setAmountError] = useState<string>("");
    const [formSuccessMessage, setFormSuccessMessage] = useState<string>("");

    const resolvedOnSubmit = onSubmit ?? createDeal;
    const resolvedOnSuccess = onSuccess ?? onCreated ?? (() => undefined);
    const resolvedTitle = title ?? (mode === "edit" ? "Edit deal" : "Create deal");
    const resolvedDescription =
        description ??
        (mode === "edit"
            ? "Update this deal and keep related entities aligned."
            : "Add a new sales opportunity for this tenant.");
    const resolvedSubmitLabel = submitLabel ?? (mode === "edit" ? "Save changes" : "Create deal");
    const resolvedSubmittingLabel = submittingLabel ?? (mode === "edit" ? "Saving..." : "Creating...");
    const resolvedSuccessMessage =
        successMessage ?? (mode === "edit" ? "Deal updated successfully." : "Deal created successfully.");

    useEffect(() => {
        setFormData(buildInitialFormState(initialValues));
        setErrorMessage("");
        setAmountError("");
        setFormSuccessMessage("");
    }, [initialValues]);

    const availableContacts = useMemo(() => {
        if (!formData.company_id) {
            return contacts;
        }

        return contacts.filter((contact) => contact.company_id === formData.company_id);
    }, [contacts, formData.company_id]);

    const activeProducts = useMemo(() => {
        return products.filter((product) => product.is_active);
    }, [products]);

    const selectedCompanyMissing =
        Boolean(formData.company_id) &&
        !companies.some((company) => company.id === formData.company_id);
    const selectedContactMissing =
        Boolean(formData.contact_id) &&
        !availableContacts.some((contact) => contact.id === formData.contact_id);
    const selectedProduct = formData.product_id
        ? products.find((product) => product.id === formData.product_id) ?? null
        : null;
    const selectedProductMissing =
        Boolean(formData.product_id) &&
        !activeProducts.some((product) => product.id === formData.product_id);

    function updateField<K extends keyof DealCreateRequest>(
        field: K,
        value: DealCreateRequest[K],
    ): void {
        setFormData((current) => ({
            ...current,
            [field]: value,
        }));
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();

        try {
            setIsSubmitting(true);
            setErrorMessage("");
            setFormSuccessMessage("");

            const amountResult = parseStrictDecimalAmountInput(formData.amount);
            if (amountResult.error || amountResult.value === null) {
                setAmountError(amountResult.error ?? TOTAL_AMOUNT_INVALID_MESSAGE);
                return;
            }

            const payload: DealCreateRequest = {
                ...formData,
                name: formData.name.trim(),
                company_id: formData.company_id,
                contact_id: formData.contact_id || null,
                product_id: formData.product_id || null,
                amount: String(amountResult.value),
                currency: formData.currency.trim().toUpperCase(),
                expected_close_date: formData.expected_close_date || null,
                notes: formData.notes?.trim() ? formData.notes.trim() : null,
            };

            await resolvedOnSubmit(payload);
            setFormSuccessMessage(resolvedSuccessMessage);
            if (mode === "create") {
                setFormData(DEFAULT_FORM_STATE);
            }
            await resolvedOnSuccess();
        } catch (error: unknown) {
            console.error("Failed to save deal:", error);
            setErrorMessage(parseApiError(error));
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">{resolvedTitle}</h2>
            <p className="mt-2 text-sm text-slate-600">
                {resolvedDescription}
            </p>

            <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-name">
                            Deal name
                        </label>
                        <input
                            id="deal-name"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.name}
                            onChange={(event) => updateField("name", event.target.value)}
                            required
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-company">
                            Company
                        </label>
                        <select
                            id="deal-company"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.company_id}
                            onChange={(event) => {
                                updateField("company_id", event.target.value);
                                updateField("contact_id", null);
                            }}
                            required
                        >
                            <option value="">Select company</option>
                            {selectedCompanyMissing ? (
                                <option value={formData.company_id}>
                                    Unknown company ({formData.company_id})
                                </option>
                            ) : null}
                            {companies.map((company) => (
                                <option key={company.id} value={company.id}>
                                    {company.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-contact">
                            Contact
                        </label>
                        <select
                            id="deal-contact"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.contact_id ?? ""}
                            onChange={(event) =>
                                updateField("contact_id", event.target.value || null)
                            }
                        >
                            <option value="">No contact</option>
                            {selectedContactMissing && formData.contact_id ? (
                                <option value={formData.contact_id}>
                                    Unknown contact ({formData.contact_id})
                                </option>
                            ) : null}
                            {availableContacts.map((contact) => (
                                <option key={contact.id} value={contact.id}>
                                    {contact.first_name} {contact.last_name ?? ""}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-product">
                            Product
                        </label>
                        <select
                            id="deal-product"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.product_id ?? ""}
                            onChange={(event) =>
                                updateField("product_id", event.target.value || null)
                            }
                        >
                            <option value="">No product</option>
                            {selectedProductMissing && formData.product_id ? (
                                <option value={formData.product_id}>
                                    {selectedProduct
                                        ? `${selectedProduct.name} (${selectedProduct.sku})${selectedProduct.is_active ? "" : " [inactive]"}`
                                        : `Unknown product (${formData.product_id})`}
                                </option>
                            ) : null}
                            {activeProducts.map((product) => (
                                <option key={product.id} value={product.id}>
                                    {product.name} ({product.sku})
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-amount">
                            Amount
                        </label>
                        <input
                            id="deal-amount"
                            type="text"
                            inputMode="decimal"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.amount}
                            onChange={(event) => {
                                updateField("amount", sanitizeStrictDecimalInput(event.target.value));
                                setAmountError("");
                            }}
                            onKeyDown={(event) => {
                                if (shouldBlockStrictDecimalKey(event.key)) {
                                    event.preventDefault();
                                }
                            }}
                            required
                        />
                        {amountError ? (
                            <p className="mt-1 text-sm text-red-600">{amountError}</p>
                        ) : null}
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-currency">
                            Currency
                        </label>
                        <input
                            id="deal-currency"
                            maxLength={3}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                            value={formData.currency}
                            onChange={(event) => updateField("currency", event.target.value)}
                            required
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-stage">
                            Stage
                        </label>
                        <select
                            id="deal-stage"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.stage}
                            onChange={(event) =>
                                updateField("stage", event.target.value as DealCreateRequest["stage"])
                            }
                            required
                        >
                            {DEAL_STAGES.map((stage) => (
                                <option key={stage} value={stage}>
                                    {formatDealLabel(stage)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-status">
                            Status
                        </label>
                        <select
                            id="deal-status"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.status}
                            onChange={(event) =>
                                updateField("status", event.target.value as DealCreateRequest["status"])
                            }
                            required
                        >
                            {DEAL_STATUSES.map((status) => (
                                <option key={status} value={status}>
                                    {formatDealLabel(status)}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-close-date">
                        Expected close date
                    </label>
                    <input
                        id="deal-close-date"
                        type="date"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        value={formData.expected_close_date ?? ""}
                        onChange={(event) =>
                            updateField("expected_close_date", event.target.value || null)
                        }
                    />
                </div>

                <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="deal-notes">
                        Notes
                    </label>
                    <textarea
                        id="deal-notes"
                        className="min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        value={formData.notes ?? ""}
                        onChange={(event) => updateField("notes", event.target.value || null)}
                    />
                </div>

                {errorMessage ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {errorMessage}
                    </div>
                ) : null}

                {formSuccessMessage ? (
                    <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
                        {formSuccessMessage}
                    </div>
                ) : null}

                <div>
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? resolvedSubmittingLabel : resolvedSubmitLabel}
                    </button>
                </div>
            </form>
        </section>
    );
}

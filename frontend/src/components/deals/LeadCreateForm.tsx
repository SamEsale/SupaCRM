"use client";

import { useEffect, useMemo, useState } from "react";

import {
    parseStrictDecimalAmountInput,
    sanitizeStrictDecimalInput,
    shouldBlockStrictDecimalKey,
    TOTAL_AMOUNT_INVALID_MESSAGE,
} from "@/components/finance/amount-utils";
import { LEAD_SOURCES, formatDealLabel } from "@/lib/deals";
import { createLead } from "@/services/deals.service";
import type { Company, Contact, Deal, LeadCreateRequest } from "@/types/crm";

type LeadCreateFormProps = {
    companies: Company[];
    contacts: Contact[];
    initialValues?: Partial<LeadCreateRequest>;
    onCreated?: (deal: Deal) => Promise<void> | void;
};

const DEFAULT_FORM_STATE: LeadCreateRequest = {
    name: "",
    company_id: "",
    contact_id: null,
    email: null,
    phone: null,
    amount: "",
    currency: "USD",
    source: "manual",
    notes: null,
};

function buildInitialFormState(
    initialValues?: Partial<LeadCreateRequest>,
): LeadCreateRequest {
    return {
        ...DEFAULT_FORM_STATE,
        ...initialValues,
        name: initialValues?.name ?? DEFAULT_FORM_STATE.name,
        company_id: initialValues?.company_id ?? DEFAULT_FORM_STATE.company_id,
        contact_id: initialValues?.contact_id ?? DEFAULT_FORM_STATE.contact_id,
        email: initialValues?.email ?? DEFAULT_FORM_STATE.email,
        phone: initialValues?.phone ?? DEFAULT_FORM_STATE.phone,
        amount: initialValues?.amount ?? DEFAULT_FORM_STATE.amount,
        currency: initialValues?.currency ?? DEFAULT_FORM_STATE.currency,
        source: initialValues?.source ?? DEFAULT_FORM_STATE.source,
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

    return "The lead could not be saved.";
}

export default function LeadCreateForm({
    companies,
    contacts,
    initialValues,
    onCreated,
}: LeadCreateFormProps) {
    const [formData, setFormData] = useState<LeadCreateRequest>(() => buildInitialFormState(initialValues));
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [amountError, setAmountError] = useState<string>("");

    useEffect(() => {
        setFormData(buildInitialFormState(initialValues));
        setErrorMessage("");
        setAmountError("");
    }, [initialValues]);

    const availableContacts = useMemo(() => {
        if (!formData.company_id) {
            return contacts;
        }

        return contacts.filter((contact) => contact.company_id === formData.company_id);
    }, [contacts, formData.company_id]);

    const selectedContact = useMemo(
        () => contacts.find((contact) => contact.id === formData.contact_id) ?? null,
        [contacts, formData.contact_id],
    );

    useEffect(() => {
        if (!formData.contact_id) {
            return;
        }

        if (!selectedContact) {
            return;
        }

        setFormData((current) => {
            const nextName = current.name || [selectedContact.first_name, selectedContact.last_name].filter(Boolean).join(" ");
            return {
                ...current,
                company_id: current.company_id || selectedContact.company_id || "",
                name: nextName,
                email: current.email ?? selectedContact.email ?? null,
                phone: current.phone ?? selectedContact.phone ?? null,
            };
        });
    }, [formData.contact_id, selectedContact]);

    function updateField<K extends keyof LeadCreateRequest>(
        field: K,
        value: LeadCreateRequest[K],
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

            const amountResult = parseStrictDecimalAmountInput(formData.amount);
            if (amountResult.error || amountResult.value === null) {
                setAmountError(amountResult.error ?? TOTAL_AMOUNT_INVALID_MESSAGE);
                return;
            }

            if (!formData.company_id.trim()) {
                setErrorMessage("Select a company before creating a lead.");
                return;
            }

            if (
                selectedContact &&
                selectedContact.company_id &&
                selectedContact.company_id !== formData.company_id
            ) {
                setErrorMessage("The selected contact does not belong to the selected company.");
                return;
            }

            const payload: LeadCreateRequest = {
                ...formData,
                name: formData.name.trim(),
                company_id: formData.company_id,
                contact_id: formData.contact_id || null,
                email: formData.email?.trim() || null,
                phone: formData.phone?.trim() || null,
                amount: String(amountResult.value),
                currency: formData.currency.trim().toUpperCase(),
                source: formData.source,
                notes: formData.notes?.trim() || null,
            };

            const deal = await createLead(payload);
            setFormData(buildInitialFormState(initialValues));
            await onCreated?.(deal);
        } catch (error: unknown) {
            console.error("Failed to save lead:", error);
            setErrorMessage(parseApiError(error));
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Add lead</h2>
            <p className="mt-2 text-sm text-slate-600">
                Capture an early-stage sales lead and persist it on the existing deals backbone at the
                <span className="font-medium text-slate-900"> New Lead</span> stage.
            </p>

            <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-name">
                            Lead name
                        </label>
                        <input
                            id="lead-name"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.name}
                            onChange={(event) => updateField("name", event.target.value)}
                            required
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-company">
                            Company
                        </label>
                        <select
                            id="lead-company"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.company_id}
                            onChange={(event) => {
                                updateField("company_id", event.target.value);
                                updateField("contact_id", null);
                            }}
                            required
                        >
                            <option value="">Select company</option>
                            {companies.map((company) => (
                                <option key={company.id} value={company.id}>
                                    {company.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-contact">
                            Contact
                        </label>
                        <select
                            id="lead-contact"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.contact_id ?? ""}
                            onChange={(event) => {
                                const nextContactId = event.target.value || null;
                                const nextContact = contacts.find((contact) => contact.id === nextContactId) ?? null;

                                updateField("contact_id", nextContactId);
                                if (nextContact?.company_id) {
                                    updateField("company_id", nextContact.company_id);
                                }
                            }}
                        >
                            <option value="">No contact</option>
                            {availableContacts.map((contact) => (
                                <option key={contact.id} value={contact.id}>
                                    {[contact.first_name, contact.last_name].filter(Boolean).join(" ")}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-source">
                            Source
                        </label>
                        <select
                            id="lead-source"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.source ?? ""}
                            onChange={(event) =>
                                updateField("source", (event.target.value || null) as LeadCreateRequest["source"])
                            }
                        >
                            {LEAD_SOURCES.map((source) => (
                                <option key={source} value={source}>
                                    {formatDealLabel(source)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-email">
                            Email
                        </label>
                        <input
                            id="lead-email"
                            type="email"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.email ?? ""}
                            onChange={(event) => updateField("email", event.target.value || null)}
                            placeholder="lead@company.com"
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-phone">
                            Phone
                        </label>
                        <input
                            id="lead-phone"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.phone ?? ""}
                            onChange={(event) => updateField("phone", event.target.value || null)}
                            placeholder="+46 555 010 101"
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-amount">
                            Amount
                        </label>
                        <input
                            id="lead-amount"
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
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-currency">
                            Currency
                        </label>
                        <input
                            id="lead-currency"
                            maxLength={3}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                            value={formData.currency}
                            onChange={(event) => updateField("currency", event.target.value)}
                            required
                        />
                    </div>
                </div>

                <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="lead-notes">
                        Notes
                    </label>
                    <textarea
                        id="lead-notes"
                        className="min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        value={formData.notes ?? ""}
                        onChange={(event) => updateField("notes", event.target.value || null)}
                        placeholder="Capture context for qualification, urgency, or next steps."
                    />
                </div>

                {errorMessage ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {errorMessage}
                    </div>
                ) : null}

                <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    This lead will be created as a deal in the <span className="font-medium">New Lead</span> stage
                    with an <span className="font-medium">Open</span> status.
                </div>

                {formData.source === "whatsapp" ? (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                        WhatsApp-sourced lead context will be preserved in the deal notes after creation.
                    </div>
                ) : null}

                <div>
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? "Creating lead..." : "Create lead"}
                    </button>
                </div>
            </form>
        </section>
    );
}

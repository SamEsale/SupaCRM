"use client";

import { useMemo, useState } from "react";

import { createDeal } from "@/services/deals.service";
import type { Company, Contact, DealCreateRequest } from "@/types/crm";
import type { Product } from "@/types/product";

type DealCreateFormProps = {
    companies: Company[];
    contacts: Contact[];
    products: Product[];
    onCreated: () => Promise<void> | void;
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

export default function DealCreateForm({
    companies,
    contacts,
    products,
    onCreated,
}: DealCreateFormProps) {
    const [formData, setFormData] = useState<DealCreateRequest>(DEFAULT_FORM_STATE);
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");

    const availableContacts = useMemo(() => {
        if (!formData.company_id) {
            return contacts;
        }

        return contacts.filter((contact) => contact.company_id === formData.company_id);
    }, [contacts, formData.company_id]);

    const activeProducts = useMemo(() => {
        return products.filter((product) => product.is_active);
    }, [products]);

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
            setSuccessMessage("");

            const payload: DealCreateRequest = {
                ...formData,
                name: formData.name.trim(),
                company_id: formData.company_id,
                contact_id: formData.contact_id || null,
                product_id: formData.product_id || null,
                amount: formData.amount.trim(),
                currency: formData.currency.trim().toUpperCase(),
                expected_close_date: formData.expected_close_date || null,
                notes: formData.notes?.trim() ? formData.notes.trim() : null,
            };

            await createDeal(payload);
            setSuccessMessage("Deal created successfully.");
            setFormData(DEFAULT_FORM_STATE);
            await onCreated();
        } catch (error: unknown) {
            console.error("Failed to create deal:", error);

            let message = "The deal could not be created.";

            if (
                typeof error === "object" &&
                error !== null &&
                "response" in error
            ) {
                const response = (error as {
                    response?: { data?: { detail?: string } };
                }).response;

                if (response?.data?.detail) {
                    message = response.data.detail;
                }
            }

            setErrorMessage(message);
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Create deal</h2>
            <p className="mt-2 text-sm text-slate-600">
                Add a new sales opportunity for this tenant.
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
                            type="number"
                            min="0"
                            step="0.01"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.amount}
                            onChange={(event) => updateField("amount", event.target.value)}
                            required
                        />
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
                            <option value="new lead">New Lead</option>
                            <option value="qualified lead">Qualified Lead</option>
                            <option value="proposal sent">Proposal Sent</option>
                            <option value="estimate sent">Estimate Sent</option>
                            <option value="negotiating contract terms">Negotiating Contract Terms</option>
                            <option value="contract signed">Contract Signed</option>
                            <option value="deal not secured">Deal Not Secured</option>
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
                            <option value="open">Open</option>
                            <option value="in progress">In Progress</option>
                            <option value="won">Won</option>
                            <option value="lost">Lost</option>
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

                {successMessage ? (
                    <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
                        {successMessage}
                    </div>
                ) : null}

                <div>
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? "Creating..." : "Create deal"}
                    </button>
                </div>
            </form>
        </section>
    );
}

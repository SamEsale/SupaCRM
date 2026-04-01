"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals } from "@/services/deals.service";
import { getProducts } from "@/services/products.service";
import { createQuote } from "@/services/quotes.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { QuoteStatus } from "@/types/finance";
import type { Product } from "@/types/product";

type QuoteFormState = {
    company_id: string;
    contact_id: string;
    deal_id: string;
    product_id: string;
    issue_date: string;
    expiry_date: string;
    currency: string;
    total_amount: string;
    status: QuoteStatus;
    notes: string;
};

type QuoteFormErrors = Partial<Record<
    "company_id" | "contact_id" | "deal_id" | "issue_date" | "expiry_date" | "currency" | "total_amount",
    string
>>;

const DEFAULT_FORM_STATE: QuoteFormState = {
    company_id: "",
    contact_id: "",
    deal_id: "",
    product_id: "",
    issue_date: "",
    expiry_date: "",
    currency: "USD",
    total_amount: "",
    status: "draft",
    notes: "",
};

const QUOTE_STATUS_OPTIONS: Array<{ value: QuoteStatus; label: string }> = [
    { value: "draft", label: "Draft" },
    { value: "sent", label: "Sent" },
    { value: "accepted", label: "Accepted" },
    { value: "rejected", label: "Rejected" },
    { value: "expired", label: "Expired" },
];

export default function CreateQuotePage() {
    const auth = useAuth();
    const router = useRouter();
    const submitLockRef = useRef(false);

    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [deals, setDeals] = useState<Deal[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [form, setForm] = useState<QuoteFormState>(DEFAULT_FORM_STATE);
    const [formErrors, setFormErrors] = useState<QuoteFormErrors>({});
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [loadError, setLoadError] = useState<string>("");
    const [submitError, setSubmitError] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadReferenceData(): Promise<void> {
            try {
                setIsLoading(true);
                setLoadError("");

                const [companiesResponse, contactsResponse, productsResponse] =
                    await Promise.all([
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                    ]);

                let dealsItems: Deal[] = [];
                try {
                    const dealsResponse = await getDeals();
                    dealsItems = dealsResponse.items ?? [];
                } catch (error) {
                    console.warn("Deals could not be loaded for quote create enrichment:", error);
                }

                if (!isMounted) {
                    return;
                }

                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setDeals(dealsItems);
                setProducts(productsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load quote create reference data:", error);

                if (!isMounted) {
                    return;
                }

                setLoadError("The quote form could not be loaded from the backend.");
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadReferenceData();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    const filteredContacts = useMemo(() => {
        if (!form.company_id) {
            return [];
        }

        return contacts.filter((contact) => contact.company_id === form.company_id);
    }, [contacts, form.company_id]);

    const filteredDeals = useMemo(() => {
        if (!form.company_id) {
            return [];
        }

        return deals.filter((deal) => deal.company_id === form.company_id);
    }, [deals, form.company_id]);

    function clearFieldError(field: keyof QuoteFormErrors): void {
        setFormErrors((current) => {
            if (!current[field]) {
                return current;
            }

            const nextErrors = { ...current };
            delete nextErrors[field];
            return nextErrors;
        });
    }

    function validateForm(): QuoteFormErrors {
        const errors: QuoteFormErrors = {};
        const currency = form.currency.trim().toUpperCase();
        const totalAmountRaw = form.total_amount.trim();
        const totalAmount = Number(totalAmountRaw);

        if (!form.company_id) {
            errors.company_id = "Company is required.";
        }

        if (form.contact_id && !filteredContacts.some((contact) => contact.id === form.contact_id)) {
            errors.contact_id = "Selected contact does not belong to the selected company.";
        }

        if (form.deal_id && !filteredDeals.some((deal) => deal.id === form.deal_id)) {
            errors.deal_id = "Selected deal does not belong to the selected company.";
        }

        if (!form.issue_date) {
            errors.issue_date = "Issue date is required.";
        }

        if (!form.expiry_date) {
            errors.expiry_date = "Expiry date is required.";
        }

        if (form.issue_date && form.expiry_date && form.expiry_date < form.issue_date) {
            errors.expiry_date = "Expiry date cannot be earlier than issue date.";
        }

        if (!currency) {
            errors.currency = "Currency is required.";
        } else if (currency.length !== 3) {
            errors.currency = "Currency must be exactly 3 characters (e.g. USD).";
        }

        if (!totalAmountRaw) {
            errors.total_amount = "Total amount is required.";
        } else if (!Number.isFinite(totalAmount)) {
            errors.total_amount = "Total amount must be a valid number.";
        } else if (totalAmount < 0) {
            errors.total_amount = "Total amount cannot be negative.";
        }

        return errors;
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();

        if (submitLockRef.current || isSubmitting) {
            return;
        }

        setSubmitError("");
        const nextErrors = validateForm();
        setFormErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0) {
            return;
        }

        try {
            submitLockRef.current = true;
            setIsSubmitting(true);

            await createQuote({
                company_id: form.company_id,
                contact_id: form.contact_id ? form.contact_id : null,
                deal_id: form.deal_id ? form.deal_id : null,
                product_id: form.product_id ? form.product_id : null,
                issue_date: form.issue_date,
                expiry_date: form.expiry_date,
                currency: form.currency.trim().toUpperCase(),
                total_amount: Number(form.total_amount.trim()),
                status: form.status,
                notes: form.notes.trim() ? form.notes.trim() : null,
            });

            router.push("/finance/quotes");
            router.refresh();
        } catch (error: unknown) {
            console.error("Failed to create quote:", error);

            let message = "Failed to create quote.";
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

            setSubmitError(message);
        } finally {
            submitLockRef.current = false;
            setIsSubmitting(false);
        }
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Create Quote</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Create a quote or estimate linked to your existing CRM records.
                        </p>
                    </div>

                    <Link
                        href="/finance/quotes"
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Back to all quotes
                    </Link>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Loading quote form
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching companies, contacts, deals, and products from the backend API.
                    </p>
                </section>
            ) : loadError ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">
                        Failed to load quote form
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">{loadError}</p>
                </section>
            ) : (
                <section className="max-w-2xl rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <form onSubmit={handleSubmit} noValidate className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Company
                            </label>
                            <select
                                value={form.company_id}
                                onChange={(event) => {
                                    const nextCompanyId = event.target.value;
                                    setForm((current) => ({
                                        ...current,
                                        company_id: nextCompanyId,
                                        contact_id: "",
                                        deal_id: "",
                                    }));
                                    clearFieldError("company_id");
                                    clearFieldError("contact_id");
                                    clearFieldError("deal_id");
                                    setSubmitError("");
                                }}
                                className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
                                    formErrors.company_id ? "border-red-500" : "border-slate-300"
                                }`}
                            >
                                <option value="">Select company</option>
                                {companies.map((company) => (
                                    <option key={company.id} value={company.id}>
                                        {company.name}
                                    </option>
                                ))}
                            </select>
                            {formErrors.company_id ? (
                                <p className="mt-1 text-sm text-red-600">{formErrors.company_id}</p>
                            ) : null}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Contact
                            </label>
                            <select
                                value={form.contact_id}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        contact_id: event.target.value,
                                    }));
                                    clearFieldError("contact_id");
                                    setSubmitError("");
                                }}
                                disabled={!form.company_id}
                                className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500 ${
                                    formErrors.contact_id ? "border-red-500" : "border-slate-300"
                                }`}
                            >
                                <option value="">
                                    {form.company_id ? "Select contact" : "Select company first"}
                                </option>
                                {filteredContacts.map((contact) => (
                                    <option key={contact.id} value={contact.id}>
                                        {[contact.first_name, contact.last_name].filter(Boolean).join(" ")}
                                    </option>
                                ))}
                            </select>
                            {formErrors.contact_id ? (
                                <p className="mt-1 text-sm text-red-600">{formErrors.contact_id}</p>
                            ) : null}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Deal
                            </label>
                            <select
                                value={form.deal_id}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        deal_id: event.target.value,
                                    }));
                                    clearFieldError("deal_id");
                                    setSubmitError("");
                                }}
                                disabled={!form.company_id}
                                className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500 ${
                                    formErrors.deal_id ? "border-red-500" : "border-slate-300"
                                }`}
                            >
                                <option value="">
                                    {form.company_id ? "Select deal" : "Select company first"}
                                </option>
                                {filteredDeals.map((deal) => (
                                    <option key={deal.id} value={deal.id}>
                                        {deal.name}
                                    </option>
                                ))}
                            </select>
                            {formErrors.deal_id ? (
                                <p className="mt-1 text-sm text-red-600">{formErrors.deal_id}</p>
                            ) : null}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Product
                            </label>
                            <select
                                value={form.product_id}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        product_id: event.target.value,
                                    }));
                                    setSubmitError("");
                                }}
                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            >
                                <option value="">Select product</option>
                                {products.map((product) => (
                                    <option key={product.id} value={product.id}>
                                        {product.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Issue Date
                            </label>
                            <input
                                type="date"
                                value={form.issue_date}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        issue_date: event.target.value,
                                    }));
                                    clearFieldError("issue_date");
                                    clearFieldError("expiry_date");
                                    setSubmitError("");
                                }}
                                className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
                                    formErrors.issue_date ? "border-red-500" : "border-slate-300"
                                }`}
                            />
                            {formErrors.issue_date ? (
                                <p className="mt-1 text-sm text-red-600">{formErrors.issue_date}</p>
                            ) : null}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Expiry Date
                            </label>
                            <input
                                type="date"
                                value={form.expiry_date}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        expiry_date: event.target.value,
                                    }));
                                    clearFieldError("expiry_date");
                                    setSubmitError("");
                                }}
                                className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
                                    formErrors.expiry_date ? "border-red-500" : "border-slate-300"
                                }`}
                            />
                            {formErrors.expiry_date ? (
                                <p className="mt-1 text-sm text-red-600">{formErrors.expiry_date}</p>
                            ) : null}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Currency
                            </label>
                            <input
                                type="text"
                                placeholder="e.g. USD"
                                value={form.currency}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        currency: event.target.value,
                                    }));
                                    clearFieldError("currency");
                                    setSubmitError("");
                                }}
                                className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
                                    formErrors.currency ? "border-red-500" : "border-slate-300"
                                }`}
                            />
                            {formErrors.currency ? (
                                <p className="mt-1 text-sm text-red-600">{formErrors.currency}</p>
                            ) : null}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Total Amount
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                placeholder="e.g. 1000.00"
                                value={form.total_amount}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        total_amount: event.target.value,
                                    }));
                                    clearFieldError("total_amount");
                                    setSubmitError("");
                                }}
                                className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
                                    formErrors.total_amount ? "border-red-500" : "border-slate-300"
                                }`}
                            />
                            {formErrors.total_amount ? (
                                <p className="mt-1 text-sm text-red-600">{formErrors.total_amount}</p>
                            ) : null}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Status
                            </label>
                            <select
                                value={form.status}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        status: event.target.value as QuoteStatus,
                                    }));
                                    setSubmitError("");
                                }}
                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            >
                                {QUOTE_STATUS_OPTIONS.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Notes
                            </label>
                            <textarea
                                placeholder="Optional notes..."
                                value={form.notes}
                                onChange={(event) => {
                                    setForm((current) => ({
                                        ...current,
                                        notes: event.target.value,
                                    }));
                                    setSubmitError("");
                                }}
                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            />
                        </div>

                        {submitError ? (
                            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                {submitError}
                            </div>
                        ) : null}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isSubmitting ? "Creating quote..." : "Create Quote"}
                        </button>
                    </form>
                </section>
            )}
        </main>
    );
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";
import { createInvoice } from "@/services/invoices.service";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getProducts } from "@/services/products.service";
import type { Company, Contact } from "@/types/crm";
import type { Product } from "@/types/product";

type InvoiceFormState = {
    company_id: string;
    contact_id: string;
    product_id: string;
    issue_date: string;
    due_date: string;
    currency: string;
    total_amount: string;
    notes: string;
};

type InvoiceFormErrors = Partial<Record<
    "company_id" | "contact_id" | "issue_date" | "due_date" | "currency" | "total_amount",
    string
>>;

const INITIAL_FORM_STATE: InvoiceFormState = {
    company_id: "",
    contact_id: "",
    product_id: "",
    issue_date: "",
    due_date: "",
    currency: "USD",
    total_amount: "",
    notes: "",
};

export default function CreateInvoicePage() {
    const auth = useAuth();
    const router = useRouter();
    const submitLockRef = useRef(false);

    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [products, setProducts] = useState<Product[]>([]);

    const [form, setForm] = useState<InvoiceFormState>(INITIAL_FORM_STATE);
    const [formErrors, setFormErrors] = useState<InvoiceFormErrors>({});
    const [submitError, setSubmitError] = useState<string>("");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            return;
        }

        let isMounted = true;

        async function load(): Promise<void> {
            try {
                const [companiesResponse, contactsResponse, productsResponse] =
                    await Promise.all([
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                    ]);

                if (!isMounted) {
                    return;
                }

                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setProducts(productsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load invoice form data:", error);
            }
        }

        void load();

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

    function clearFieldError(field: keyof InvoiceFormErrors): void {
        setFormErrors((current) => {
            if (!current[field]) {
                return current;
            }

            const nextErrors = { ...current };
            delete nextErrors[field];
            return nextErrors;
        });
    }

    function validateForm(): InvoiceFormErrors {
        const errors: InvoiceFormErrors = {};
        const currency = form.currency.trim().toUpperCase();
        const totalAmountRaw = form.total_amount.trim();
        const totalAmount = Number(totalAmountRaw);

        if (!form.company_id) {
            errors.company_id = "Company is required.";
        }

        if (form.contact_id && !filteredContacts.some((contact) => contact.id === form.contact_id)) {
            errors.contact_id = "Selected contact does not belong to the selected company.";
        }

        if (!form.issue_date) {
            errors.issue_date = "Issue date is required.";
        }

        if (!form.due_date) {
            errors.due_date = "Due date is required.";
        }

        if (form.issue_date && form.due_date && form.due_date < form.issue_date) {
            errors.due_date = "Due date cannot be earlier than issue date.";
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

        if (submitLockRef.current || loading) {
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
            setLoading(true);

            await createInvoice({
                company_id: form.company_id,
                contact_id: form.contact_id ? form.contact_id : null,
                product_id: form.product_id ? form.product_id : null,
                issue_date: form.issue_date,
                due_date: form.due_date,
                currency: form.currency.trim().toUpperCase(),
                total_amount: Number(form.total_amount.trim()),
                notes: form.notes.trim() ? form.notes.trim() : null,
            });

            router.push("/finance/invoices");
            router.refresh();
        } catch (error: unknown) {
            console.error("Failed to create invoice:", error);
            let message = "Failed to create invoice.";

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
            setLoading(false);
            submitLockRef.current = false;
        }
    }

    return (
        <main className="space-y-6">
            <section className="max-w-2xl rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-2xl font-bold text-slate-900">
                    Create Invoice
                </h1>

                <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-4">
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
                                }));
                                clearFieldError("company_id");
                                clearFieldError("contact_id");
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
                                clearFieldError("due_date");
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
                            Due Date
                        </label>
                        <input
                            type="date"
                            value={form.due_date}
                            onChange={(event) => {
                                setForm((current) => ({
                                    ...current,
                                    due_date: event.target.value,
                                }));
                                clearFieldError("due_date");
                                setSubmitError("");
                            }}
                            className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
                                formErrors.due_date ? "border-red-500" : "border-slate-300"
                            }`}
                        />
                        {formErrors.due_date ? (
                            <p className="mt-1 text-sm text-red-600">{formErrors.due_date}</p>
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
                        disabled={loading}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {loading ? "Creating invoice..." : "Create Invoice"}
                    </button>
                </form>
            </section>
        </main>
    );
}

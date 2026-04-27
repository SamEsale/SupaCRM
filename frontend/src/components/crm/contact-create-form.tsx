"use client";

import { useEffect, useMemo, useState } from "react";

import { getCompanies } from "@/services/companies.service";
import { createContact } from "@/services/contacts.service";
import type { Company, ContactCreateRequest } from "@/types/crm";

type ContactFormMode = "create" | "edit";

interface Props {
    onCreated?: () => void;
    onSuccess?: () => void;
    onSubmit?: (payload: ContactCreateRequest) => Promise<void>;
    initialValues?: Partial<ContactCreateRequest>;
    mode?: ContactFormMode;
    title?: string;
    description?: string;
    submitLabel?: string;
    submittingLabel?: string;
}

const initialState: ContactCreateRequest = {
    first_name: "",
    last_name: null,
    email: null,
    phone: null,
    company_id: null,
    company: null,
    job_title: null,
    notes: null,
};

function buildInitialState(
    initialValues?: Partial<ContactCreateRequest>,
): ContactCreateRequest {
    return {
        ...initialState,
        ...initialValues,
    };
}

function parseErrorMessage(error: unknown): string {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
            return response.data.detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "Failed to save contact";
}

export default function ContactCreateForm({
    onCreated,
    onSuccess,
    onSubmit,
    initialValues,
    mode = "create",
    title,
    description,
    submitLabel,
    submittingLabel,
}: Props) {
    const [form, setForm] = useState<ContactCreateRequest>(() =>
        buildInitialState(initialValues),
    );
    const [companies, setCompanies] = useState<Company[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isCompaniesLoading, setIsCompaniesLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const resolvedSubmit = onSubmit ?? createContact;
    const resolvedOnSuccess = onSuccess ?? onCreated ?? (() => undefined);
    const resolvedTitle = title ?? (mode === "edit" ? "Edit contact" : "Create contact");
    const resolvedDescription =
        description ??
        (mode === "edit"
            ? "Update contact details and save changes."
            : "Create a new contact and optionally link it to an existing company.");
    const resolvedSubmitLabel = submitLabel ?? (mode === "edit" ? "Save changes" : "Create Contact");
    const resolvedSubmittingLabel = submittingLabel ?? (mode === "edit" ? "Saving..." : "Creating...");

    useEffect(() => {
        setForm(buildInitialState(initialValues));
        setError(null);
    }, [initialValues]);

    useEffect(() => {
        let isMounted = true;

        async function loadCompanies() {
            try {
                setIsCompaniesLoading(true);
                const res = await getCompanies();
                if (!isMounted) {
                    return;
                }
                setCompanies(res.items ?? []);
            } catch (err) {
                console.error("Failed to load companies", err);
            } finally {
                if (isMounted) {
                    setIsCompaniesLoading(false);
                }
            }
        }

        void loadCompanies();

        return () => {
            isMounted = false;
        };
    }, []);

    const selectedCompanyMissing = useMemo(() => {
        if (!form.company_id) {
            return false;
        }
        return !companies.some((company) => company.id === form.company_id);
    }, [companies, form.company_id]);

    function handleChange(
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
    ): void {
        const { name, value } = e.target;

        setForm((prev) => ({
            ...prev,
            [name]: value === "" ? null : value,
        }));
    }

    async function handleSubmit(e: React.FormEvent): Promise<void> {
        e.preventDefault();
        setError(null);
        setIsSubmitting(true);

        try {
            const firstName = form.first_name?.trim() ?? "";
            if (!firstName) {
                throw new Error("First name is required");
            }

            const selectedCompany = companies.find((company) => company.id === form.company_id);

            const payload: ContactCreateRequest = {
                ...form,
                first_name: firstName,
                last_name: form.last_name?.trim() ? form.last_name.trim() : null,
                email: form.email?.trim() ? form.email.trim() : null,
                phone: form.phone?.trim() ? form.phone.trim() : null,
                company_id: form.company_id,
                company: selectedCompany?.name ?? form.company ?? null,
                job_title: form.job_title?.trim() ? form.job_title.trim() : null,
                notes: form.notes?.trim() ? form.notes.trim() : null,
            };

            await resolvedSubmit(payload);

            if (mode === "create") {
                setForm(initialState);
            }

            await Promise.resolve(resolvedOnSuccess());
        } catch (err: unknown) {
            setError(parseErrorMessage(err));
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
            <h2 className="text-xl font-semibold text-slate-900">
                {resolvedTitle}
            </h2>
            <p className="text-sm text-slate-600">{resolvedDescription}</p>

            <div className="grid grid-cols-2 gap-4">
                <input
                    name="first_name"
                    placeholder="First name *"
                    value={form.first_name ?? ""}
                    onChange={handleChange}
                    className="rounded-lg border px-3 py-2 text-sm"
                    required
                />

                <input
                    name="last_name"
                    placeholder="Last name"
                    value={form.last_name ?? ""}
                    onChange={handleChange}
                    className="rounded-lg border px-3 py-2 text-sm"
                />
            </div>

            <div className="grid grid-cols-2 gap-4">
                <input
                    name="email"
                    placeholder="Email"
                    value={form.email ?? ""}
                    onChange={handleChange}
                    className="rounded-lg border px-3 py-2 text-sm"
                />

                <input
                    name="phone"
                    placeholder="Phone"
                    value={form.phone ?? ""}
                    onChange={handleChange}
                    className="rounded-lg border px-3 py-2 text-sm"
                />
            </div>

            <select
                name="company_id"
                value={form.company_id ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                disabled={isCompaniesLoading}
            >
                <option value="">Select company (optional)</option>
                {selectedCompanyMissing && form.company_id ? (
                    <option value={form.company_id}>
                        Unknown company ({form.company_id})
                    </option>
                ) : null}
                {companies.map((company) => (
                    <option key={company.id} value={company.id}>
                        {company.name}
                    </option>
                ))}
            </select>

            <input
                name="job_title"
                placeholder="Job title"
                value={form.job_title ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            <textarea
                name="notes"
                placeholder="Notes"
                value={form.notes ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            {error ? <div className="text-sm text-red-600">{error}</div> : null}

            <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
                {isSubmitting ? resolvedSubmittingLabel : resolvedSubmitLabel}
            </button>
        </form>
    );
}

"use client";

import { useEffect, useState } from "react";

import { createContact } from "@/services/contacts.service";
import { getCompanies } from "@/services/companies.service";
import type { Company, ContactCreateRequest } from "@/types/crm";

interface Props {
    onCreated?: () => void;
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

export default function ContactCreateForm({ onCreated }: Props) {
    const [form, setForm] = useState<ContactCreateRequest>(initialState);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadCompanies() {
            try {
                const res = await getCompanies();
                setCompanies(res.items ?? []);
            } catch (err) {
                console.error("Failed to load companies", err);
            }
        }

        loadCompanies();
    }, []);

    function handleChange(
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
    ) {
        const { name, value } = e.target;

        setForm((prev) => ({
            ...prev,
            [name]: value === "" ? null : value,
        }));
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError(null);
        setIsSubmitting(true);

        try {
            if (!form.first_name) {
                throw new Error("First name is required");
            }

            await createContact(form);

            setForm(initialState);

            if (onCreated) {
                onCreated();
            }
        } catch (err: any) {
            setError(err.message || "Failed to create contact");
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
                Create Contact
            </h2>

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
                    onChange={handleChange}
                    className="rounded-lg border px-3 py-2 text-sm"
                />
            </div>

            <div className="grid grid-cols-2 gap-4">
                <input
                    name="email"
                    placeholder="Email"
                    onChange={handleChange}
                    className="rounded-lg border px-3 py-2 text-sm"
                />

                <input
                    name="phone"
                    placeholder="Phone"
                    onChange={handleChange}
                    className="rounded-lg border px-3 py-2 text-sm"
                />
            </div>

            <select
                name="company_id"
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            >
                <option value="">Select company (optional)</option>
                {companies.map((company) => (
                    <option key={company.id} value={company.id}>
                        {company.name}
                    </option>
                ))}
            </select>

            <input
                name="job_title"
                placeholder="Job title"
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            <textarea
                name="notes"
                placeholder="Notes"
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            {error && <div className="text-sm text-red-600">{error}</div>}

            <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm text-white"
            >
                {isSubmitting ? "Creating..." : "Create Contact"}
            </button>
        </form>
    );
}

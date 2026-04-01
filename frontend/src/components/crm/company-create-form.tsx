"use client";

import { useState } from "react";

import { createCompany } from "@/services/companies.service";
import type { CompanyCreateRequest } from "@/types/crm";

interface Props {
    onCreated?: () => void;
}

const initialState: CompanyCreateRequest = {
    name: "",
    website: null,
    email: null,
    phone: null,
    industry: null,
    address: null,
    vat_number: null,
    registration_number: null,
    notes: null,
};

export default function CompanyCreateForm({ onCreated }: Props) {
    const [form, setForm] = useState<CompanyCreateRequest>(initialState);

    const [street, setStreet] = useState("");
    const [unit, setUnit] = useState("");
    const [postalCode, setPostalCode] = useState("");
    const [city, setCity] = useState("");
    const [state, setStateValue] = useState("");
    const [country, setCountry] = useState("");

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    function handleChange(
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) {
        const { name, value } = e.target;

        setForm((prev) => ({
            ...prev,
            [name]: value.trim() === "" ? null : value,
        }));
    }

    function buildAddress(): string | null {
        const parts = [
            street,
            unit,
            postalCode,
            city,
            state,
            country,
        ].filter((p) => p && p.trim() !== "");

        return parts.length > 0 ? parts.join(", ") : null;
    }

    function resetAddressFields() {
        setStreet("");
        setUnit("");
        setPostalCode("");
        setCity("");
        setStateValue("");
        setCountry("");
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError(null);
        setIsSubmitting(true);

        try {
            if (!form.name || form.name.trim() === "") {
                throw new Error("Company name is required");
            }

            const payload: CompanyCreateRequest = {
                ...form,
                address: buildAddress(),
            };

            await createCompany(payload);

            setForm(initialState);
            resetAddressFields();

            if (onCreated) {
                onCreated();
            }
        } catch (err: any) {
            setError(err.message || "Failed to create company");
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
                Create Company
            </h2>

            <input
                name="name"
                placeholder="Company Name *"
                value={form.name ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                required
            />

            <input
                name="website"
                placeholder="Website"
                value={form.website ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            <input
                name="email"
                placeholder="Email"
                value={form.email ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            <input
                name="phone"
                placeholder="Phone"
                value={form.phone ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            <input
                name="industry"
                placeholder="Industry"
                value={form.industry ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            {/* Address Row */}
            <div className="grid grid-cols-6 gap-2">
                <input
                    placeholder="Street"
                    value={street}
                    onChange={(e) => setStreet(e.target.value)}
                    className="col-span-2 rounded-lg border px-2 py-2 text-sm"
                />
                <input
                    placeholder="Unit"
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    className="rounded-lg border px-2 py-2 text-sm"
                />
                <input
                    placeholder="Postal"
                    value={postalCode}
                    onChange={(e) => setPostalCode(e.target.value)}
                    className="rounded-lg border px-2 py-2 text-sm"
                />
                <input
                    placeholder="City"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="rounded-lg border px-2 py-2 text-sm"
                />
                <input
                    placeholder="Country"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    className="rounded-lg border px-2 py-2 text-sm"
                />
            </div>

            <textarea
                name="notes"
                placeholder="Notes"
                value={form.notes ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            {error && (
                <div className="text-sm text-red-600">{error}</div>
            )}

            <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm text-white"
            >
                {isSubmitting ? "Creating..." : "Create Company"}
            </button>
        </form>
    );
}

"use client";

import { useEffect, useState } from "react";

import {
    buildCompanyAddress,
    getCountryOptions,
    parseCompanyAddress,
} from "@/components/crm/company-address-utils";
import { createCompany } from "@/services/companies.service";
import type { CompanyCreateRequest } from "@/types/crm";

type CompanyFormMode = "create" | "edit";

interface Props {
    onCreated?: () => void;
    onSuccess?: () => void;
    onSubmit?: (payload: CompanyCreateRequest) => Promise<void>;
    initialValues?: Partial<CompanyCreateRequest>;
    mode?: CompanyFormMode;
    title?: string;
    description?: string;
    submitLabel?: string;
    submittingLabel?: string;
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

function buildInitialState(
    initialValues?: Partial<CompanyCreateRequest>,
): CompanyCreateRequest {
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

    return "Failed to save company.";
}

export default function CompanyCreateForm({
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
    const parsedInitialAddress = parseCompanyAddress(initialValues?.address);

    const [form, setForm] = useState<CompanyCreateRequest>(() =>
        buildInitialState(initialValues),
    );

    const [street, setStreet] = useState<string>(parsedInitialAddress.street);
    const [unit, setUnit] = useState<string>(parsedInitialAddress.unit);
    const [postalCode, setPostalCode] = useState<string>(parsedInitialAddress.postalCode);
    const [city, setCity] = useState<string>(parsedInitialAddress.city);
    const [country, setCountry] = useState<string>(parsedInitialAddress.country);
    const [stateCounty, setStateCounty] = useState<string>(parsedInitialAddress.stateCounty);

    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const resolvedSubmit = onSubmit ?? createCompany;
    const resolvedOnSuccess = onSuccess ?? onCreated ?? (() => undefined);
    const resolvedTitle = title ?? (mode === "edit" ? "Edit company" : "Create company");
    const resolvedDescription =
        description ??
        (mode === "edit"
            ? "Update company details and save changes."
            : "Create a new company record.");
    const resolvedSubmitLabel = submitLabel ?? (mode === "edit" ? "Save changes" : "Create Company");
    const resolvedSubmittingLabel = submittingLabel ?? (mode === "edit" ? "Saving..." : "Creating...");

    useEffect(() => {
        const nextAddress = parseCompanyAddress(initialValues?.address);

        setForm(buildInitialState(initialValues));
        setStreet(nextAddress.street);
        setUnit(nextAddress.unit);
        setPostalCode(nextAddress.postalCode);
        setCity(nextAddress.city);
        setCountry(nextAddress.country);
        setStateCounty(nextAddress.stateCounty);
        setError(null);
    }, [initialValues]);

    function handleChange(
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ): void {
        const { name, value } = e.target;

        setForm((prev) => ({
            ...prev,
            [name]: value.trim() === "" ? null : value,
        }));
    }

    function buildAddress(): string | null {
        return buildCompanyAddress({
            street,
            unit,
            postalCode,
            city,
            country,
            stateCounty,
        });
    }

    function resetAddressFields(): void {
        setStreet("");
        setUnit("");
        setPostalCode("");
        setCity("");
        setStateCounty("");
        setCountry("Sweden");
    }

    async function handleSubmit(e: React.FormEvent): Promise<void> {
        e.preventDefault();
        setError(null);
        setIsSubmitting(true);

        try {
            const companyName = form.name?.trim() ?? "";
            if (!companyName) {
                throw new Error("Company name is required");
            }

            const payload: CompanyCreateRequest = {
                ...form,
                name: companyName,
                website: form.website?.trim() ? form.website.trim() : null,
                email: form.email?.trim() ? form.email.trim() : null,
                phone: form.phone?.trim() ? form.phone.trim() : null,
                industry: form.industry?.trim() ? form.industry.trim() : null,
                vat_number: form.vat_number?.trim() ? form.vat_number.trim() : null,
                registration_number: form.registration_number?.trim()
                    ? form.registration_number.trim()
                    : null,
                notes: form.notes?.trim() ? form.notes.trim() : null,
                address: buildAddress(),
            };

            await resolvedSubmit(payload);

            if (mode === "create") {
                setForm(initialState);
                resetAddressFields();
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

            <div className="grid grid-cols-7 gap-2">
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
                <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="company-state-county">
                        State / County
                    </label>
                    <input
                        id="company-state-county"
                        value={stateCounty}
                        onChange={(e) => setStateCounty(e.target.value)}
                        className="w-full rounded-lg border px-2 py-2 text-sm"
                    />
                </div>
                <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="company-country">
                        Country
                    </label>
                    <select
                        id="company-country"
                        value={country}
                        onChange={(e) => setCountry(e.target.value)}
                        className="w-full rounded-lg border px-2 py-2 text-sm bg-white"
                    >
                        {getCountryOptions().map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <input
                name="vat_number"
                placeholder="VAT Number"
                value={form.vat_number ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border px-3 py-2 text-sm"
            />

            <input
                name="registration_number"
                placeholder="Registration Number"
                value={form.registration_number ?? ""}
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

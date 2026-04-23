"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import LeadCreateForm from "@/components/deals/LeadCreateForm";
import { LEAD_SOURCES } from "@/lib/deals";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import type { Company, Contact, Deal, LeadCreateRequest, LeadSource } from "@/types/crm";

function resolveLeadSource(value: string | null): LeadSource | null {
    if (!value) {
        return null;
    }

    return LEAD_SOURCES.includes(value as LeadSource) ? (value as LeadSource) : null;
}

export default function CreateLeadPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [resolvedInitialValues, setResolvedInitialValues] = useState<Partial<LeadCreateRequest>>({});

    const seededInitialValues = useMemo<Partial<LeadCreateRequest>>(() => {
        const seededNotes = [
            searchParams.get("notes"),
            searchParams.get("message"),
            searchParams.get("campaign") ? `Campaign: ${searchParams.get("campaign")}` : null,
        ]
            .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
            .join("\n");

        return {
            name: searchParams.get("name") ?? "",
            company_id: searchParams.get("company_id") ?? "",
            contact_id: searchParams.get("contact_id"),
            email: searchParams.get("email"),
            phone: searchParams.get("phone"),
            amount: searchParams.get("amount") ?? "",
            currency: searchParams.get("currency") ?? "USD",
            source: resolveLeadSource(searchParams.get("source")) ?? "manual",
            notes: seededNotes || null,
        };
    }, [searchParams]);

    useEffect(() => {
        async function loadReferenceData(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const [companiesResponse, contactsResponse] = await Promise.all([
                    getCompanies(),
                    getContacts(),
                ]);

                const availableCompanies = companiesResponse.items ?? [];
                const availableContacts = contactsResponse.items ?? [];
                const seededCompanyId = seededInitialValues.company_id?.trim() || "";
                const seededContactId = seededInitialValues.contact_id?.trim() || "";

                const selectedCompany = seededCompanyId
                    ? availableCompanies.find((company) => company.id === seededCompanyId) ?? null
                    : null;
                const selectedContact = seededContactId
                    ? availableContacts.find((contact) => contact.id === seededContactId) ?? null
                    : null;

                if (seededCompanyId && !selectedCompany) {
                    setCompanies(availableCompanies);
                    setContacts(availableContacts);
                    setResolvedInitialValues({});
                    setErrorMessage("The selected company could not be found for this tenant.");
                    return;
                }

                if (seededContactId && !selectedContact) {
                    setCompanies(availableCompanies);
                    setContacts(availableContacts);
                    setResolvedInitialValues({});
                    setErrorMessage("The selected contact could not be found for this tenant.");
                    return;
                }

                if (
                    selectedContact &&
                    selectedCompany &&
                    selectedContact.company_id &&
                    selectedContact.company_id !== selectedCompany.id
                ) {
                    setCompanies(availableCompanies);
                    setContacts(availableContacts);
                    setResolvedInitialValues({});
                    setErrorMessage("The selected contact does not belong to the selected company.");
                    return;
                }

                if (selectedContact && !selectedContact.company_id && !selectedCompany) {
                    setCompanies(availableCompanies);
                    setContacts(availableContacts);
                    setResolvedInitialValues({});
                    setErrorMessage("The selected contact must be linked to a company before creating a lead.");
                    return;
                }

                const resolvedCompanyId = selectedContact?.company_id ?? selectedCompany?.id ?? "";
                const resolvedName = seededInitialValues.name?.trim()
                    || [selectedContact?.first_name, selectedContact?.last_name].filter(Boolean).join(" ")
                    || selectedCompany?.name
                    || "";

                setCompanies(availableCompanies);
                setContacts(availableContacts);
                setResolvedInitialValues({
                    ...seededInitialValues,
                    name: resolvedName,
                    company_id: resolvedCompanyId,
                    contact_id: selectedContact?.id ?? null,
                    email: selectedContact?.email ?? seededInitialValues.email ?? null,
                    phone: selectedContact?.phone ?? seededInitialValues.phone ?? null,
                });
            } catch (error) {
                console.error("Failed to load lead form data:", error);
                setErrorMessage("The lead intake form could not be loaded from the backend.");
            } finally {
                setIsLoading(false);
            }
        }

        void loadReferenceData();
    }, [seededInitialValues]);

    function handleCreated(deal: Deal): void {
        router.push(`/deals/${deal.id}?createdFrom=lead-intake`);
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Add Lead</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Capture an early-stage opportunity and keep it on the existing deal lifecycle from
                    qualification through quoting.
                </p>
                {resolvedInitialValues.contact_id ? (
                    <p className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                        Starting from a contact record. CRM contact, company, email, and phone context were prefilled.
                    </p>
                ) : resolvedInitialValues.company_id ? (
                    <p className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                        Starting from a company record. Company context was prefilled for this lead.
                    </p>
                ) : null}
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading lead form</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching companies and contacts from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load lead form</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : (
                <LeadCreateForm
                    companies={companies}
                    contacts={contacts}
                    initialValues={resolvedInitialValues}
                    onCreated={handleCreated}
                />
            )}
        </main>
    );
}

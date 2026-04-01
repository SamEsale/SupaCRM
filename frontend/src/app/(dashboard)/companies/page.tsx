"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import CompaniesList from "@/components/crm/companies-list";
import { getCompanies } from "@/services/companies.service";
import type { Company } from "@/types/crm";

function matchesCompany(company: Company, searchTerm: string): boolean {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    if (!normalizedSearch) {
        return true;
    }

    const haystack = [
        company.name,
        company.website,
        company.email,
        company.phone,
        company.industry,
        company.address,
        company.vat_number,
        company.registration_number,
        company.notes,
    ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

    return haystack.includes(normalizedSearch);
}

export default function CompaniesPage() {
    const [companies, setCompanies] = useState<Company[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [searchTerm, setSearchTerm] = useState<string>("");

    const loadCompanies = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");

            const response = await getCompanies();
            setCompanies(response.items ?? []);
        } catch (error) {
            console.error("Failed to load companies:", error);
            setErrorMessage("The companies list could not be loaded.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadCompanies();
    }, [loadCompanies]);

    const filteredCompanies = useMemo(() => {
        return companies.filter((company) => matchesCompany(company, searchTerm));
    }, [companies, searchTerm]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">All Companies</h1>

                <div className="mt-6">
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Search companies by name, address, VAT number, registration number, website, email, phone, or industry"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />
                </div>
            </section>

            {isLoading ? (
                <div className="rounded-xl bg-white p-6">Loading...</div>
            ) : errorMessage ? (
                <div className="rounded-xl bg-white p-6 text-red-600">{errorMessage}</div>
            ) : (
                <CompaniesList
                    companies={filteredCompanies}
                    total={filteredCompanies.length}
                />
            )}
        </main>
    );
}

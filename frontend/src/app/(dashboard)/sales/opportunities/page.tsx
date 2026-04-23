"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import DealsList from "@/components/deals/DealsList";
import { OPPORTUNITY_DEAL_STAGES, formatDealLabel } from "@/lib/deals";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals } from "@/services/deals.service";
import { getProducts } from "@/services/products.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Product } from "@/types/product";

function getCompanyName(companyId: string, companies: Company[]): string {
    return companies.find((company) => company.id === companyId)?.name ?? "";
}

function getContactName(contactId: string | null, contacts: Contact[]): string {
    if (!contactId) {
        return "";
    }

    const contact = contacts.find((item) => item.id === contactId);
    if (!contact) {
        return "";
    }

    return [contact.first_name, contact.last_name].filter(Boolean).join(" ");
}

function getProductName(productId: string | null, products: Product[]): string {
    if (!productId) {
        return "";
    }

    return products.find((product) => product.id === productId)?.name ?? "";
}

function matchesOpportunity(
    deal: Deal,
    searchTerm: string,
    companies: Company[],
    contacts: Contact[],
    products: Product[],
): boolean {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    if (!normalizedSearch) {
        return true;
    }

    const haystack = [
        deal.name,
        deal.amount,
        deal.currency,
        deal.stage,
        deal.status,
        deal.expected_close_date,
        deal.notes,
        getCompanyName(deal.company_id, companies),
        getContactName(deal.contact_id, contacts),
        getProductName(deal.product_id, products),
    ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

    return haystack.includes(normalizedSearch);
}

export default function OpportunitiesPage() {
    const [deals, setDeals] = useState<Deal[]>([]);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [searchTerm, setSearchTerm] = useState<string>("");
    const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

    const loadPageData = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");

            const [dealsResponse, companiesResponse, contactsResponse, productsResponse] =
                await Promise.all([
                    getDeals({ view: "opportunities" }),
                    getCompanies(),
                    getContacts(),
                    getProducts(),
                ]);

            setDeals(dealsResponse.items ?? []);
            setCompanies(companiesResponse.items ?? []);
            setContacts(contactsResponse.items ?? []);
            setProducts(productsResponse.items ?? []);
        } catch (error) {
            console.error("Failed to load opportunities page data:", error);
            setErrorMessage("The opportunities view could not be loaded from the backend.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadPageData();
    }, [loadPageData]);

    const filteredDeals = useMemo(() => {
        return deals.filter((deal) => {
            const matchesSearch = matchesOpportunity(deal, searchTerm, companies, contacts, products);
            const matchesCompany = selectedCompanyId === "" || deal.company_id === selectedCompanyId;
            return matchesSearch && matchesCompany;
        });
    }, [companies, contacts, deals, products, searchTerm, selectedCompanyId]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Opportunities</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Opportunities are active, revenue-bearing deals in the stages from{" "}
                    <span className="font-medium text-slate-900">
                        {OPPORTUNITY_DEAL_STAGES.map((stage) => formatDealLabel(stage)).join(", ")}
                    </span>
                    .
                </p>

                <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(event) => setSearchTerm(event.target.value)}
                        placeholder="Search opportunities by name, company, contact, product, status, or amount"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />

                    <select
                        value={selectedCompanyId}
                        onChange={(event) => setSelectedCompanyId(event.target.value)}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    >
                        <option value="">All companies</option>
                        {companies.map((company) => (
                            <option key={company.id} value={company.id}>
                                {company.name}
                            </option>
                        ))}
                    </select>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading opportunities</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching active opportunities, companies, contacts, and products from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load opportunities</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                    <button
                        type="button"
                        onClick={() => {
                            void loadPageData();
                        }}
                        className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Retry
                    </button>
                </section>
            ) : filteredDeals.length === 0 ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">No open opportunities</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        No qualifying deals matched the current opportunity filter and UI filters.
                    </p>
                </section>
            ) : (
                <DealsList
                    deals={filteredDeals}
                    total={filteredDeals.length}
                    companies={companies}
                    contacts={contacts}
                    products={products}
                    title="Open opportunities"
                    description="currently in the qualified, proposal, estimate, or negotiation stages."
                />
            )}
        </main>
    );
}

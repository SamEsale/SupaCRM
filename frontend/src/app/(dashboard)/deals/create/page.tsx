"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import DealCreateForm from "@/components/deals/DealCreateForm";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getProducts } from "@/services/products.service";
import type { Company, Contact } from "@/types/crm";
import type { Product } from "@/types/product";

export default function CreateDealPage() {
    const router = useRouter();
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    useEffect(() => {
        async function loadReferenceData(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const [companiesResponse, contactsResponse, productsResponse] =
                    await Promise.all([
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                    ]);

                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setProducts(productsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load create deal page data:", error);
                setErrorMessage("The deal form could not be loaded from the backend.");
            } finally {
                setIsLoading(false);
            }
        }

        void loadReferenceData();
    }, []);

    function handleCreated(): void {
        router.push("/deals");
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Add Deal</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Create a new deal and link it to a company, contact, and product.
                </p>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Loading deal form
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching companies, contacts, and products from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">
                        Failed to load deal form
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : (
                <DealCreateForm
                    companies={companies}
                    contacts={contacts}
                    products={products}
                    onCreated={handleCreated}
                />
            )}
        </main>
    );
}

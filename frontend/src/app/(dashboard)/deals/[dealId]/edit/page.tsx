"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import DealCreateForm from "@/components/deals/DealCreateForm";
import DealFollowUpCard from "@/components/deals/DealFollowUpCard";
import { useAuth } from "@/hooks/use-auth";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDealById, updateDeal } from "@/services/deals.service";
import { getProducts } from "@/services/products.service";
import type { Company, Contact, Deal, DealCreateRequest } from "@/types/crm";
import type { Product } from "@/types/product";

function getLoadErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Deal not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The deal edit form could not be loaded from the backend.";
}

export default function EditDealPage() {
    const auth = useAuth();
    const router = useRouter();
    const params = useParams<{ dealId: string }>();
    const rawDealId = params?.dealId;
    const dealId = Array.isArray(rawDealId) ? rawDealId[0] : rawDealId;

    const [deal, setDeal] = useState<Deal | null>(null);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        if (!dealId) {
            setErrorMessage("Invalid deal id.");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadPageData(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const [dealResponse, companiesResponse, contactsResponse, productsResponse] =
                    await Promise.all([
                        getDealById(dealId),
                        getCompanies(),
                        getContacts(),
                        getProducts(),
                    ]);

                if (!isMounted) {
                    return;
                }

                setDeal(dealResponse);
                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setProducts(productsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load deal edit page:", error);
                if (!isMounted) {
                    return;
                }

                setDeal(null);
                setErrorMessage(getLoadErrorMessage(error));
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadPageData();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, dealId]);

    const initialValues = useMemo<Partial<DealCreateRequest> | undefined>(() => {
        if (!deal) {
            return undefined;
        }

        return {
            name: deal.name,
            company_id: deal.company_id,
            contact_id: deal.contact_id,
            product_id: deal.product_id,
            amount: deal.amount,
            currency: deal.currency,
            stage: deal.stage,
            status: deal.status,
            expected_close_date: deal.expected_close_date,
            notes: deal.notes,
        };
    }, [deal]);

    async function handleSave(payload: DealCreateRequest): Promise<void> {
        if (!dealId) {
            throw new Error("Invalid deal id.");
        }

        await updateDeal(dealId, payload);
    }

    function handleSaved(): void {
        if (!dealId) {
            return;
        }

        router.push(`/deals/${dealId}`);
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Edit Deal</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Update deal details while preserving company, contact, and product relationships.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {dealId ? (
                            <Link
                                href={`/deals/${dealId}`}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                            >
                                Back to deal detail
                            </Link>
                        ) : null}
                        <Link
                            href="/deals"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all deals
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading deal edit form</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching current deal, companies, contacts, and products from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load deal edit form</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !deal ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Deal unavailable</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested deal could not be found.
                    </p>
                </section>
            ) : (
                <>
                    <DealCreateForm
                        mode="edit"
                        companies={companies}
                        contacts={contacts}
                        products={products}
                        initialValues={initialValues}
                        onSubmit={handleSave}
                        onSuccess={handleSaved}
                        title="Edit deal"
                        description="Modify deal fields and save changes."
                        submitLabel="Save changes"
                        submittingLabel="Saving..."
                        successMessage="Deal updated successfully."
                    />

                    <DealFollowUpCard
                        deal={deal}
                        onUpdated={(updatedDeal) => {
                            setDeal(updatedDeal);
                        }}
                    />
                </>
            )}
        </main>
    );
}

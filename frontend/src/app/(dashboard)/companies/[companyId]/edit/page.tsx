"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import CompanyCreateForm from "@/components/crm/company-create-form";
import { useAuth } from "@/hooks/use-auth";
import { getCompanyById, updateCompany } from "@/services/companies.service";
import type { Company, CompanyCreateRequest } from "@/types/crm";

function getLoadErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Company not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The company edit form could not be loaded from the backend.";
}

export default function EditCompanyPage() {
    const auth = useAuth();
    const router = useRouter();
    const params = useParams<{ companyId: string }>();
    const rawCompanyId = params?.companyId;
    const companyId = Array.isArray(rawCompanyId) ? rawCompanyId[0] : rawCompanyId;

    const [company, setCompany] = useState<Company | null>(null);
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

        if (!companyId) {
            setErrorMessage("Invalid company id.");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadCompany(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const companyResponse = await getCompanyById(companyId);

                if (!isMounted) {
                    return;
                }

                setCompany(companyResponse);
            } catch (error) {
                console.error("Failed to load company edit page:", error);
                if (!isMounted) {
                    return;
                }

                setCompany(null);
                setErrorMessage(getLoadErrorMessage(error));
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadCompany();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, companyId]);

    const initialValues = useMemo<Partial<CompanyCreateRequest> | undefined>(() => {
        if (!company) {
            return undefined;
        }

        return {
            name: company.name,
            website: company.website,
            email: company.email,
            phone: company.phone,
            industry: company.industry,
            address: company.address,
            vat_number: company.vat_number,
            registration_number: company.registration_number,
            notes: company.notes,
        };
    }, [company]);

    async function handleSave(payload: CompanyCreateRequest): Promise<void> {
        if (!companyId) {
            throw new Error("Invalid company id.");
        }

        await updateCompany(companyId, payload);
    }

    function handleSaved(): void {
        if (!companyId) {
            return;
        }

        router.push(`/companies/${companyId}`);
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Edit Company</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Update company details and save changes.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {companyId ? (
                            <Link
                                href={`/companies/${companyId}`}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                            >
                                Back to company detail
                            </Link>
                        ) : null}
                        <Link
                            href="/companies"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all companies
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading company edit form</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching current company data from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load company edit form</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !company ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Company unavailable</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested company could not be found.
                    </p>
                </section>
            ) : (
                <CompanyCreateForm
                    mode="edit"
                    initialValues={initialValues}
                    onSubmit={handleSave}
                    onSuccess={handleSaved}
                    title="Edit company"
                    description="Modify company fields and save changes."
                    submitLabel="Save changes"
                    submittingLabel="Saving..."
                />
            )}
        </main>
    );
}

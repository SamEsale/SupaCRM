"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import SupportTicketForm from "@/components/support/SupportTicketForm";
import { useAuth } from "@/hooks/use-auth";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getDeals } from "@/services/deals.service";
import { getInvoices } from "@/services/invoices.service";
import { getTenantUsers } from "@/services/tenants.service";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Invoice } from "@/types/finance";
import type { TenantUser } from "@/types/tenants";
import type { SupportTicket } from "@/types/support";

export default function CreateSupportTicketPage() {
    const auth = useAuth();
    const router = useRouter();
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [tenantUsers, setTenantUsers] = useState<TenantUser[]>([]);
    const [deals, setDeals] = useState<Deal[]>([]);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
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

        let isMounted = true;

        async function loadReferenceData(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const [
                    companiesResponse,
                    contactsResponse,
                    tenantUsersResponse,
                    dealsResponse,
                    invoicesResponse,
                ] = await Promise.all([
                    getCompanies(),
                    getContacts(),
                    getTenantUsers(),
                    getDeals({ limit: 100 }),
                    getInvoices({ limit: 100 }),
                ]);

                if (!isMounted) {
                    return;
                }

                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setTenantUsers(tenantUsersResponse ?? []);
                setDeals(dealsResponse.items ?? []);
                setInvoices(invoicesResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load support create page:", error);
                if (isMounted) {
                    setErrorMessage("The support ticket form could not be loaded from the backend.");
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadReferenceData();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    function handleCreated(ticket: SupportTicket): void {
        router.push(`/support/${ticket.id}`);
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Create Ticket</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Capture a support issue with tenant-safe CRM and commercial context from the start.
                        </p>
                    </div>
                    <Link
                        href="/support"
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Back to all tickets
                    </Link>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading support ticket form</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching companies, contacts, assignees, deals, and invoices from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load support ticket form</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : (
                <SupportTicketForm
                    companies={companies}
                    contacts={contacts}
                    tenantUsers={tenantUsers}
                    deals={deals}
                    invoices={invoices}
                    onSuccess={handleCreated}
                    title="Create support ticket"
                    description="Create a real support record and link it back into the right customer and revenue context."
                    submitLabel="Create ticket"
                    submittingLabel="Creating..."
                    successMessage="Ticket created successfully."
                />
            )}
        </main>
    );
}

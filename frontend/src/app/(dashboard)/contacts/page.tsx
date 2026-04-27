"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import ContactsCsvOperationsCard from "@/components/crm/ContactsCsvOperationsCard";
import ContactsList from "@/components/crm/contacts-list";
import { buildLeadCreateHref } from "@/lib/deals";
import { deleteContact, getContacts } from "@/services/contacts.service";
import type { Contact } from "@/types/crm";

function matchesContact(contact: Contact, searchTerm: string): boolean {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    if (!normalizedSearch) {
        return true;
    }

    const haystack = [
        contact.first_name,
        contact.last_name,
        contact.email,
        contact.phone,
        contact.company,
        contact.job_title,
        contact.notes,
    ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

    return haystack.includes(normalizedSearch);
}

export default function ContactsPage() {
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [actionMessage, setActionMessage] = useState<string>("");
    const [searchTerm, setSearchTerm] = useState<string>("");

    const loadContacts = useCallback(async (): Promise<void> => {
        try {
            setIsLoading(true);
            setErrorMessage("");

            const response = await getContacts();

            setContacts(response.items ?? []);
        } catch (error) {
            console.error("Failed to load contacts:", error);

            setErrorMessage("The contacts list could not be loaded from the backend.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadContacts();
    }, [loadContacts]);

    async function handleDeleteContact(contact: Contact): Promise<void> {
        const contactName = [contact.first_name, contact.last_name].filter(Boolean).join(" ") || contact.id;
        const confirmed = window.confirm(`Delete ${contactName}? This action cannot be undone.`);
        if (!confirmed) {
            return;
        }

        try {
            setActionMessage("");
            await deleteContact(contact.id);
            setActionMessage(`Deleted ${contactName}.`);
            await loadContacts();
        } catch (error: unknown) {
            console.error("Failed to delete contact:", error);
            const detail =
                typeof error === "object" &&
                error !== null &&
                "response" in error &&
                typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
                    ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
                    : null;
            setActionMessage(detail ?? "Failed to delete contact.");
        }
    }

    const filteredContacts = useMemo(() => {
        return contacts.filter((contact) => matchesContact(contact, searchTerm));
    }, [contacts, searchTerm]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">All Contacts</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Search and review all contacts stored in your CRM, then move the right person into the live Lead to Deal workflow.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        <Link
                            href={buildLeadCreateHref()}
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Add Lead
                        </Link>
                        <Link
                            href="/contacts/create"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        >
                            Add Contact
                        </Link>
                    </div>
                </div>

                <div className="mt-6">
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(event) => setSearchTerm(event.target.value)}
                        placeholder="Search contacts by name, email, phone, company, or job title"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />
                </div>

                {actionMessage ? (
                    <p className="mt-4 text-sm text-slate-700">{actionMessage}</p>
                ) : null}
            </section>

            <ContactsCsvOperationsCard
                exportQuery={{
                    q: searchTerm.trim() || undefined,
                }}
            />

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        Loading contacts
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching contacts from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">
                        Failed to load contacts
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : filteredContacts.length === 0 ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        No contacts found
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        No contacts matched your current search.
                    </p>
                </section>
            ) : (
                <ContactsList
                    contacts={filteredContacts}
                    total={filteredContacts.length}
                    onDeleteContact={handleDeleteContact}
                />
            )}
        </main>
    );
}

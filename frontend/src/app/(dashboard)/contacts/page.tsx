"use client";

import { useEffect, useMemo, useState } from "react";

import ContactsList from "@/components/crm/contacts-list";
import { getContacts } from "@/services/contacts.service";
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
    const [searchTerm, setSearchTerm] = useState<string>("");

    useEffect(() => {
        let isMounted = true;

        async function loadContacts(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const response = await getContacts();

                if (!isMounted) {
                    return;
                }

                setContacts(response.items ?? []);
            } catch (error) {
                console.error("Failed to load contacts:", error);

                if (!isMounted) {
                    return;
                }

                setErrorMessage("The contacts list could not be loaded from the backend.");
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        loadContacts();

        return () => {
            isMounted = false;
        };
    }, []);

    const filteredContacts = useMemo(() => {
        return contacts.filter((contact) => matchesContact(contact, searchTerm));
    }, [contacts, searchTerm]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">All Contacts</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Search and review all contacts stored in your CRM.
                </p>

                <div className="mt-6">
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(event) => setSearchTerm(event.target.value)}
                        placeholder="Search contacts by name, email, phone, company, or job title"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />
                </div>
            </section>

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
                <ContactsList contacts={filteredContacts} total={filteredContacts.length} />
            )}
        </main>
    );
}

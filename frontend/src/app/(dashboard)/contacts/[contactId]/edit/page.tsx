"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import ContactCreateForm from "@/components/crm/contact-create-form";
import { useAuth } from "@/hooks/use-auth";
import { getContactById, updateContact } from "@/services/contacts.service";
import type { Contact, ContactCreateRequest } from "@/types/crm";

function getLoadErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Contact not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The contact edit form could not be loaded from the backend.";
}

export default function EditContactPage() {
    const auth = useAuth();
    const router = useRouter();
    const params = useParams<{ contactId: string }>();
    const rawContactId = params?.contactId;
    const contactId = Array.isArray(rawContactId) ? rawContactId[0] : rawContactId;

    const [contact, setContact] = useState<Contact | null>(null);
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

        if (!contactId) {
            setErrorMessage("Invalid contact id.");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadContact(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const contactResponse = await getContactById(contactId);

                if (!isMounted) {
                    return;
                }

                setContact(contactResponse);
            } catch (error) {
                console.error("Failed to load contact edit page:", error);
                if (!isMounted) {
                    return;
                }

                setContact(null);
                setErrorMessage(getLoadErrorMessage(error));
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadContact();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, contactId]);

    const initialValues = useMemo<Partial<ContactCreateRequest> | undefined>(() => {
        if (!contact) {
            return undefined;
        }

        return {
            first_name: contact.first_name,
            last_name: contact.last_name,
            email: contact.email,
            phone: contact.phone,
            company_id: contact.company_id,
            company: contact.company,
            job_title: contact.job_title,
            notes: contact.notes,
        };
    }, [contact]);

    async function handleSave(payload: ContactCreateRequest): Promise<void> {
        if (!contactId) {
            throw new Error("Invalid contact id.");
        }

        await updateContact(contactId, payload);
    }

    function handleSaved(): void {
        if (!contactId) {
            return;
        }

        router.push(`/contacts/${contactId}`);
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Edit Contact</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Update contact details and save changes.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {contactId ? (
                            <Link
                                href={`/contacts/${contactId}`}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                            >
                                Back to contact detail
                            </Link>
                        ) : null}
                        <Link
                            href="/contacts"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all contacts
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading contact edit form</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching current contact data from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load contact edit form</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !contact ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Contact unavailable</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested contact could not be found.
                    </p>
                </section>
            ) : (
                <ContactCreateForm
                    mode="edit"
                    initialValues={initialValues}
                    onSubmit={handleSave}
                    onSuccess={handleSaved}
                    title="Edit contact"
                    description="Modify contact fields and save changes."
                    submitLabel="Save changes"
                    submittingLabel="Saving..."
                />
            )}
        </main>
    );
}

"use client";

import { useRouter } from "next/navigation";

import ContactCreateForm from "@/components/crm/contact-create-form";

export default function CreateContactPage() {
    const router = useRouter();

    function handleCreated() {
        router.push("/contacts");
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Add Contact</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Create a new contact and optionally link it to an existing company.
                </p>
            </section>

            <ContactCreateForm onCreated={handleCreated} />
        </main>
    );
}

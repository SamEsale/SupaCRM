"use client";

import { useRouter } from "next/navigation";

import CompanyCreateForm from "@/components/crm/company-create-form";

export default function CreateCompanyPage() {
    const router = useRouter();

    function handleCreated() {
        router.push("/companies");
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold">Add Company</h1>
                <p className="text-sm text-slate-600 mt-2">
                    Create a new company record.
                </p>
            </section>

            <CompanyCreateForm onCreated={handleCreated} />
        </main>
    );
}

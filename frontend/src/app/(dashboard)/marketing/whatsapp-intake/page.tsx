"use client";

import WhatsAppLeadIntakeForm from "@/components/marketing/WhatsAppLeadIntakeForm";

export default function WhatsAppLeadIntakePage() {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">WhatsApp Intake</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Capture inbound WhatsApp context, connect it to CRM records, and push it straight onto the existing deal-backed lead flow.
                </p>
            </section>

            <WhatsAppLeadIntakeForm />
        </main>
    );
}

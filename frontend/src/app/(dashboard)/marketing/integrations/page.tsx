"use client";

import MarketingIntegrationsForm from "@/components/marketing/MarketingIntegrationsForm";

export default function MarketingIntegrationsPage() {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Marketing Integrations</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Configure WhatsApp Business and outbound SMTP settings for the tenant.
                </p>
            </section>

            <MarketingIntegrationsForm />
        </main>
    );
}


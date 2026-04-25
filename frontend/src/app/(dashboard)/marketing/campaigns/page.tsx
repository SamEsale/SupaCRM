"use client";

import MarketingCampaignsManager from "@/components/marketing/MarketingCampaignsManager";

export default function MarketingCampaignsPage() {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Campaigns</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Create and refine launch-scope campaign drafts that stay grounded in your tenant CRM and WhatsApp-first workflow.
                </p>
            </section>

            <MarketingCampaignsManager />
        </main>
    );
}

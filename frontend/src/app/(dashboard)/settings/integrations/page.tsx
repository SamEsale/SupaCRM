"use client";

import MarketingIntegrationsForm from "@/components/marketing/MarketingIntegrationsForm";
import SettingsPageFrame from "@/components/settings/SettingsPageFrame";

export default function SettingsIntegrationsPage() {
    return (
        <SettingsPageFrame
            title="Integrations"
            description="Manage the tenant communication settings that already power live product flows, including WhatsApp configuration and SMTP sender identity."
        >
            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm text-slate-600">
                    These settings are operator-facing only. Secrets remain masked after save, and the UI does not claim a live provider connection when the product only stores configuration.
                </p>
            </section>
            <MarketingIntegrationsForm />
        </SettingsPageFrame>
    );
}

import TenantCompanySettingsForm from "@/components/settings/TenantCompanySettingsForm";

export default function CompanySettingsPage() {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Company Settings</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Maintain the tenant legal profile, workspace address, VAT details, and base currency configuration.
                </p>
            </section>

            <TenantCompanySettingsForm />
        </main>
    );
}

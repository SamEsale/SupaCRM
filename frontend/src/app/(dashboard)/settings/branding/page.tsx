import TenantBrandingForm from "@/components/settings/TenantBrandingForm";

export default function BrandingPage() {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Branding</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Review the current logo reference and update the tenant brand and sidebar color values already stored in the backend.
                </p>
            </section>

            <TenantBrandingForm />
        </main>
    );
}

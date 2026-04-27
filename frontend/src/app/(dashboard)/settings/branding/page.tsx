import BrandingLogoCard from "@/components/settings/BrandingLogoCard";
import TenantBrandingForm from "@/components/settings/TenantBrandingForm";

export default function BrandingPage() {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Branding</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Manage the tenant logo and keep brand colors aligned with the values already stored in the backend.
                </p>
            </section>

            <BrandingLogoCard />
            <TenantBrandingForm />
        </main>
    );
}

import Link from "next/link";

export default function DashboardPage() {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
                <p className="mt-2 max-w-3xl text-sm text-slate-600">
                    Use the active modules below to work across CRM, finance, product catalog, billing, and tenant settings. This dashboard intentionally links to real implemented surfaces instead of placeholder metrics.
                </p>
            </section>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {[
                    ["/contacts", "Contacts", "Review and search tenant contacts."],
                    ["/companies", "Companies", "Manage linked customer companies."],
                    ["/deals", "Deals", "Track deal progress across sales stages."],
                    ["/products", "Products", "Maintain the product catalog used across sales and finance."],
                    ["/finance", "Finance", "Access invoices, quotes, and billing surfaces."],
                    ["/settings", "Settings", "Configure workspace company and branding settings."],
                ].map(([href, title, description]) => (
                    <Link
                        key={href}
                        href={href}
                        className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
                    >
                        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
                        <p className="mt-2 text-sm text-slate-600">{description}</p>
                    </Link>
                ))}
            </section>
        </main>
    );
}

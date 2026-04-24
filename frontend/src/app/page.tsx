import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-100 px-6 py-12">
      <div className="mx-auto max-w-5xl space-y-6">
        <section className="rounded-xl border border-slate-200 bg-white p-10 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            SupaCRM
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-900">
            CRM, finance, and workspace settings on a shared tenant foundation
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">
            Sign in to access the current workspace modules: contacts, companies, deals, products, finance flows, billing, and tenant settings.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/login"
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
            >
              Create Workspace
            </Link>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[
            ["Contacts", "Browse CRM contacts and linked companies."],
            ["Sales", "Track deals and finance handoff through quotes and invoices."],
            ["Products", "Manage the active catalog used by sales and invoicing."],
            ["Finance", "Work with invoices, quotes, and subscription billing."],
            ["Settings", "Maintain tenant company profile, currency defaults, and branding."],
            ["Auth", "Tenant-aware login and registration are available now."],
          ].map(([title, description]) => (
            <div key={title} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
              <p className="mt-2 text-sm text-slate-600">{description}</p>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}

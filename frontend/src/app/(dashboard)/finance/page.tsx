export default function FinancePage() {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Finance</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Manage accounting operations, invoices, quotes, expenses, and payment tracking.
                </p>
            </section>

            <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-semibold text-slate-900">Invoices</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Review issued invoices and track payment status.
                    </p>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-semibold text-slate-900">Quotes</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Prepare and manage customer quotations before invoicing.
                    </p>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-semibold text-slate-900">Expenses</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Record internal operating expenses and accounting entries.
                    </p>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-semibold text-slate-900">Payments</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Monitor received payments and reconcile finance activity.
                    </p>
                </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h2 className="text-2xl font-semibold text-slate-900">Finance Module Status</h2>
                <p className="mt-2 text-sm text-slate-600">
                    This is the initial scaffold for the Finance module. Functional invoice, quote, and expense workflows will be added in the next sequential steps.
                </p>
            </section>
        </main>
    );
}

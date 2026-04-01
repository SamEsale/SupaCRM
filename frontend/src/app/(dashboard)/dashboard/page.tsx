export default function DashboardPage() {
    return (
        <main className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>

            <p className="mt-2 text-sm text-slate-600">
                You are signed in and viewing a protected route.
            </p>

            <div className="mt-6 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
                The authenticated dashboard shell is now active.
            </div>
        </main>
    );
}
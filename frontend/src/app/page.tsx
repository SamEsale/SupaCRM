import Link from "next/link";

export default function HomePage() {
    return (
        <main className="min-h-screen bg-slate-100 px-6 py-16">
            <section className="mx-auto max-w-3xl rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
                    SupaCRM
                </p>

                <h1 className="mt-4 text-3xl font-bold text-slate-950">
                    Sign in to continue
                </h1>

                <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">
                    Access to this workspace is restricted. Sign in with an authorized account
                    or create a workspace to continue.
                </p>

                <div className="mt-8 flex flex-wrap gap-3">
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
        </main>
    );
}

export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
      <div className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white p-10 shadow-sm">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          SupaCRM Frontend
        </h1>

        <p className="mt-4 text-sm leading-6 text-slate-600">
          Frontend initialization is complete. The authentication flow and
          dashboard UI will be added in the next steps.
        </p>

        <div className="mt-6 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
          <p>Current status:</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Next.js App Router initialized</li>
            <li>TypeScript configured</li>
            <li>TailwindCSS configured</li>
            <li>Base frontend folders created</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
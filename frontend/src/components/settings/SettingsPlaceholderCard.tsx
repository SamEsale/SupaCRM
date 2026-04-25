interface SettingsPlaceholderCardProps {
    title: string;
    body: string;
}

export default function SettingsPlaceholderCard({
    title,
    body,
}: SettingsPlaceholderCardProps) {
    return (
        <section className="rounded-xl border border-dashed border-slate-300 bg-white p-8 shadow-sm">
            <div className="max-w-2xl">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    In Progress
                </p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-900">{title}</h2>
                <p className="mt-3 text-sm leading-6 text-slate-600">{body}</p>
            </div>
        </section>
    );
}

import SettingsSectionNav from "@/components/settings/SettingsSectionNav";

interface SettingsPageFrameProps {
    title: string;
    description: string;
    children: React.ReactNode;
}

export default function SettingsPageFrame({
    title,
    description,
    children,
}: SettingsPageFrameProps) {
    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Settings
                </p>
                <h1 className="mt-2 text-3xl font-bold text-slate-900">{title}</h1>
                <p className="mt-2 max-w-3xl text-sm text-slate-600">{description}</p>
            </section>

            <SettingsSectionNav />

            {children}
        </main>
    );
}

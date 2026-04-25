"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const settingsNavigationItems = [
    { href: "/settings/company", label: "Company" },
    { href: "/settings/branding", label: "Branding" },
    { href: "/settings/integrations", label: "Integrations" },
    { href: "/settings/users", label: "Users & Roles" },
    { href: "/settings/membership", label: "Membership" },
    { href: "/settings/security", label: "Security" },
];

export default function SettingsSectionNav() {
    const pathname = usePathname();

    return (
        <nav
            aria-label="Settings sections"
            className="rounded-xl border border-slate-200 bg-white p-2 shadow-sm"
        >
            <div className="flex flex-wrap gap-2">
                {settingsNavigationItems.map((item) => {
                    const isActive = pathname === item.href;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                                isActive
                                    ? "bg-slate-900 text-white"
                                    : "text-slate-700 hover:bg-slate-100"
                            }`}
                        >
                            {item.label}
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}

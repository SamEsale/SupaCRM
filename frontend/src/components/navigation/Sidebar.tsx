"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";

import TenantBrandBlock from "@/components/navigation/TenantBrandBlock";
import type { TenantBranding } from "@/types/settings";
import { sidebarMenu } from "./sidebar-menu";

function ChevronIcon({ isOpen }: { isOpen: boolean }) {
    return (
        <svg
            className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
        >
            <path
                fillRule="evenodd"
                d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
                clipRule="evenodd"
            />
        </svg>
    );
}

type SidebarProps = {
    branding: TenantBranding | null;
};

export default function Sidebar({
    branding,
}: SidebarProps) {
    const pathname = usePathname();
    const [openSectionTitle, setOpenSectionTitle] = useState<string | null>(null);

    const activeSectionTitle = useMemo(() => {
        const matchingSection = sidebarMenu.find((section) =>
            section.items.some((item) => item.href === pathname),
        );

        return matchingSection?.title ?? null;
    }, [pathname]);

    function handleToggle(sectionTitle: string): void {
        setOpenSectionTitle((currentValue) =>
            currentValue === sectionTitle ? null : sectionTitle,
        );
    }

    return (
        <aside
            className="flex h-full w-64 shrink-0 flex-col bg-[var(--sidebar-bg)] text-[var(--sidebar-text)]"
            style={{
                backgroundColor: "var(--sidebar-bg)",
                color: "var(--sidebar-text)",
            }}
        >
            <div className="border-b border-[var(--sidebar-border)] px-4 py-5">
                <TenantBrandBlock branding={branding} tone="dark" size="compact" />
            </div>

            <nav className="flex-1 overflow-y-auto px-3 py-4">
                <div className="space-y-2">
                    {sidebarMenu.map((section) => {
                        const isOpen =
                            openSectionTitle === section.title ||
                            (openSectionTitle === null && activeSectionTitle === section.title);
                        const isCurrentSection = activeSectionTitle === section.title;

                        return (
                            <div key={section.title} className="rounded-lg">
                                <button
                                    type="button"
                                    onClick={() => handleToggle(section.title)}
                                    className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                                        isOpen || isCurrentSection
                                            ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)]"
                                            : "text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover-bg)] hover:text-[var(--sidebar-text)]"
                                    }`}
                                    aria-expanded={isOpen}
                                >
                                    <span>{section.title}</span>
                                    <ChevronIcon isOpen={isOpen} />
                                </button>

                                {isOpen ? (
                                    <div className="mt-2 space-y-1 pl-2">
                                        {section.items.map((item) => {
                                            const isActiveLink =
                                                Boolean(item.href) &&
                                                pathname === item.href;

                                            if (!item.href || item.disabled) {
                                                return (
                                                    <div
                                                        key={item.title}
                                                        className="rounded-md px-3 py-2 text-sm text-[var(--sidebar-muted-text)]"
                                                    >
                                                        {item.title}
                                                        <span className="ml-2 text-xs text-[var(--sidebar-muted-text)] opacity-75">
                                                            Coming soon
                                                        </span>
                                                    </div>
                                                );
                                            }

                                            return (
                                                <Link
                                                    key={item.title}
                                                    href={item.href}
                                                    className={`block rounded-md px-3 py-2 text-sm transition ${
                                                        isActiveLink
                                                            ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)]"
                                                            : "text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover-bg)] hover:text-[var(--sidebar-text)]"
                                                    }`}
                                                >
                                                    {item.title}
                                                </Link>
                                            );
                                        })}
                                    </div>
                                ) : null}
                            </div>
                        );
                    })}
                </div>
            </nav>
        </aside>
    );
}

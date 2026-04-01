"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";

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

export default function Sidebar() {
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
        <aside className="flex h-full w-64 shrink-0 flex-col bg-slate-950 text-white">
            <div className="border-b border-slate-800 px-4 py-5">
                <h1 className="text-xl font-bold">SupaCRM</h1>
            </div>

            <nav className="flex-1 overflow-y-auto px-3 py-4">
                <div className="space-y-2">
                    {sidebarMenu.map((section) => {
                        const isOpen = openSectionTitle === section.title;
                        const isCurrentSection = activeSectionTitle === section.title;

                        return (
                            <div key={section.title} className="rounded-lg">
                                <button
                                    type="button"
                                    onClick={() => handleToggle(section.title)}
                                    className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                                        isOpen || isCurrentSection
                                            ? "bg-slate-800 text-white"
                                            : "text-slate-300 hover:bg-slate-900 hover:text-white"
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
                                                        className="rounded-md px-3 py-2 text-sm text-slate-500"
                                                    >
                                                        {item.title}
                                                        <span className="ml-2 text-xs text-slate-600">
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
                                                            ? "bg-slate-700 text-white"
                                                            : "text-slate-300 hover:bg-slate-800 hover:text-white"
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

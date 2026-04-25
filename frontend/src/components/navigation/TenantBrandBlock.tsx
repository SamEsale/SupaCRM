"use client";

import { resolveStoredMediaUrl } from "@/services/media-url";
import type { TenantBranding } from "@/types/settings";

type TenantBrandBlockProps = {
    branding: TenantBranding | null;
    subtitle?: string | null;
    tone?: "light" | "dark";
    size?: "compact" | "default";
};

export default function TenantBrandBlock({
    branding,
    subtitle = null,
    tone = "light",
    size = "default",
}: TenantBrandBlockProps) {
    const logoUrl = resolveStoredMediaUrl(branding);
    const isDark = tone === "dark";
    const isCompact = size === "compact";

    const nameClassName = isCompact
        ? `text-lg font-semibold ${isDark ? "text-[var(--sidebar-text)]" : "text-slate-900"}`
        : `text-xl font-bold ${isDark ? "text-[var(--sidebar-text)]" : "text-slate-900"}`;
    const subtitleClassName = `text-sm ${isDark ? "text-[var(--sidebar-muted-text)]" : "text-slate-600"}`;
    const fallbackClassName = isDark
        ? "border border-[var(--sidebar-border)] bg-[var(--sidebar-hover-bg)] text-[var(--sidebar-text)]"
        : "border border-transparent bg-[var(--brand-primary)] text-[var(--brand-primary-contrast)]";
    const logoSizeClassName = isCompact ? "h-9 w-9" : "h-10 w-10";

    return (
        <div className="flex min-w-0 items-center gap-3">
            {logoUrl ? (
                <img
                    src={logoUrl}
                    alt="Tenant logo"
                    className={`${logoSizeClassName} shrink-0 rounded-lg object-contain ${
                        isDark ? "bg-[var(--sidebar-hover-bg)] p-1" : "bg-white p-1 shadow-sm"
                    }`}
                />
            ) : (
                <div
                    className={`${logoSizeClassName} flex shrink-0 items-center justify-center rounded-lg text-sm font-semibold ${fallbackClassName}`}
                    aria-hidden="true"
                >
                    SC
                </div>
            )}

            <div className="min-w-0">
                <p className={`${nameClassName} truncate`}>SupaCRM</p>
                {subtitle ? (
                    <p className={`${subtitleClassName} truncate`}>{subtitle}</p>
                ) : null}
            </div>
        </div>
    );
}

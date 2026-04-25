import type { TenantBranding } from "@/types/settings";
import type { Tenant } from "@/types/tenants";

export const DEFAULT_TENANT_THEME = {
    brandPrimary: "#2563EB",
    brandSecondary: "#1D4ED8",
    sidebarBackground: "#111827",
    sidebarText: "#FFFFFF",
} as const;

export type TenantThemeInput = Pick<
    TenantBranding | Tenant,
    "brand_primary_color" | "brand_secondary_color" | "sidebar_background_color" | "sidebar_text_color"
>;

export type ResolvedTenantTheme = {
    brandPrimary: string;
    brandPrimaryContrast: string;
    brandSecondary: string;
    sidebarBackground: string;
    sidebarText: string;
    sidebarMutedText: string;
    sidebarBorder: string;
    sidebarHoverBackground: string;
    sidebarActiveBackground: string;
    sidebarActiveText: string;
};

function normalizeHex(value: string | null | undefined): string | null {
    if (!value) {
        return null;
    }

    const normalized = value.trim().toUpperCase();
    return /^#[0-9A-F]{6}$/.test(normalized) ? normalized : null;
}

function hexToRgb(value: string): { r: number; g: number; b: number } {
    return {
        r: Number.parseInt(value.slice(1, 3), 16),
        g: Number.parseInt(value.slice(3, 5), 16),
        b: Number.parseInt(value.slice(5, 7), 16),
    };
}

function rgbToHex(red: number, green: number, blue: number): string {
    return `#${[red, green, blue]
        .map((value) => Math.max(0, Math.min(255, Math.round(value))).toString(16).padStart(2, "0"))
        .join("")
        .toUpperCase()}`;
}

function mixHex(base: string, overlay: string, ratio: number): string {
    const baseRgb = hexToRgb(base);
    const overlayRgb = hexToRgb(overlay);
    const clampedRatio = Math.max(0, Math.min(1, ratio));

    return rgbToHex(
        baseRgb.r + (overlayRgb.r - baseRgb.r) * clampedRatio,
        baseRgb.g + (overlayRgb.g - baseRgb.g) * clampedRatio,
        baseRgb.b + (overlayRgb.b - baseRgb.b) * clampedRatio,
    );
}

function getContrastTextColor(background: string): string {
    const { r, g, b } = hexToRgb(background);
    const [sr, sg, sb] = [r, g, b].map((value) => {
        const normalized = value / 255;
        return normalized <= 0.03928
            ? normalized / 12.92
            : ((normalized + 0.055) / 1.055) ** 2.4;
    });
    const luminance = 0.2126 * sr + 0.7152 * sg + 0.0722 * sb;
    return luminance > 0.55 ? "#0F172A" : "#FFFFFF";
}

export function resolveTenantTheme(branding: TenantThemeInput | null | undefined): ResolvedTenantTheme {
    const brandPrimary = normalizeHex(branding?.brand_primary_color) ?? DEFAULT_TENANT_THEME.brandPrimary;
    const brandSecondary = normalizeHex(branding?.brand_secondary_color) ?? DEFAULT_TENANT_THEME.brandSecondary;
    const sidebarBackground = normalizeHex(branding?.sidebar_background_color) ?? DEFAULT_TENANT_THEME.sidebarBackground;
    const sidebarText = normalizeHex(branding?.sidebar_text_color) ?? DEFAULT_TENANT_THEME.sidebarText;
    const sidebarHoverBackground = mixHex(sidebarBackground, sidebarText, 0.12);
    const sidebarBorder = mixHex(sidebarBackground, sidebarText, 0.18);
    const sidebarMutedText = mixHex(sidebarBackground, sidebarText, 0.7);
    const sidebarActiveBackground = mixHex(sidebarBackground, brandPrimary, 0.34);

    return {
        brandPrimary,
        brandPrimaryContrast: getContrastTextColor(brandPrimary),
        brandSecondary,
        sidebarBackground,
        sidebarText,
        sidebarMutedText,
        sidebarBorder,
        sidebarHoverBackground,
        sidebarActiveBackground,
        sidebarActiveText: getContrastTextColor(sidebarActiveBackground),
    };
}

export function applyTenantTheme(theme: ResolvedTenantTheme): void {
    if (typeof document === "undefined") {
        return;
    }

    const root = document.documentElement;
    root.style.setProperty("--brand-primary", theme.brandPrimary);
    root.style.setProperty("--brand-primary-contrast", theme.brandPrimaryContrast);
    root.style.setProperty("--brand-secondary", theme.brandSecondary);
    root.style.setProperty("--sidebar-bg", theme.sidebarBackground);
    root.style.setProperty("--sidebar-text", theme.sidebarText);
    root.style.setProperty("--sidebar-muted-text", theme.sidebarMutedText);
    root.style.setProperty("--sidebar-border", theme.sidebarBorder);
    root.style.setProperty("--sidebar-hover-bg", theme.sidebarHoverBackground);
    root.style.setProperty("--sidebar-active-bg", theme.sidebarActiveBackground);
    root.style.setProperty("--sidebar-active-text", theme.sidebarActiveText);
}

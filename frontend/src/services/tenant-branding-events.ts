export const TENANT_BRANDING_CHANGED_EVENT = "tenant-branding-changed";

export function notifyTenantBrandingChanged(): void {
    if (typeof window === "undefined") {
        return;
    }

    window.dispatchEvent(new Event(TENANT_BRANDING_CHANGED_EVENT));
}

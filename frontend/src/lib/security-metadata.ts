export const PERMISSION_DESCRIPTIONS: Record<string, string> = {
    "crm.read": "Read CRM records",
    "crm.write": "Create and update CRM records",
    "crm.delete": "Delete CRM records",
    "sales.read": "Read sales data",
    "sales.write": "Create and update sales data",
    "sales.delete": "Delete sales data",
    "reporting.read": "Read reports and dashboards",
    "support.read": "Read support data",
    "support.write": "Create and update support data",
    "billing.access": "Access billing and subscription features",
    "tenant.admin": "Manage tenant administration settings",
};

export const ROLE_DESCRIPTIONS: Record<string, string> = {
    owner: "Full tenant administration with ownership accountability and billing access.",
    admin: "Operational administrator for tenant settings, billing, and day-to-day oversight.",
    manager: "Team lead access for CRM, sales, reporting, and support coordination.",
    user: "Baseline operational access for core CRM, sales, and support workflows.",
};

export interface SecuritySafeguard {
    title: string;
    body: string;
}

export const TENANT_SECURITY_SAFEGUARDS: SecuritySafeguard[] = [
    {
        title: "Tenant-scoped requests",
        body: "Protected API requests carry both a bearer token and an X-Tenant-Id header, and SupaCRM rejects tenant mismatches.",
    },
    {
        title: "Membership-gated access",
        body: "Authenticated access requires an active tenant, an active user account, and an active tenant membership.",
    },
    {
        title: "Role-based enforcement",
        body: "Administrative Settings routes are guarded by tenant.admin, which is resolved from tenant role assignments.",
    },
    {
        title: "Short-lived auth cache",
        body: "Principal and profile snapshots are short-lived and invalidated after logout, password reset, and membership ownership changes.",
    },
];

export function describePermission(permissionCode: string): string {
    return PERMISSION_DESCRIPTIONS[permissionCode] ?? permissionCode;
}

export function describeRole(roleName: string): string {
    return ROLE_DESCRIPTIONS[roleName] ?? "Tenant-scoped role defined in the current RBAC model.";
}

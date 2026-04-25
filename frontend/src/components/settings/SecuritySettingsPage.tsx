"use client";

import { useEffect, useState } from "react";

import LogoutButton from "@/components/auth/logout-button";
import { useAuth } from "@/hooks/use-auth";
import {
    TENANT_SECURITY_SAFEGUARDS,
    describePermission,
    describeRole,
} from "@/lib/security-metadata";
import {
    getCurrentUser,
    requestPasswordReset,
} from "@/services/auth.service";
import {
    getCurrentTenant,
    getTenantRoles,
    getTenantUsers,
} from "@/services/tenants.service";
import type { CurrentUserResponse } from "@/types/auth";
import type { Tenant, TenantRole, TenantUser } from "@/types/tenants";

interface SecuritySnapshot {
    currentUser: CurrentUserResponse;
    tenant: Tenant;
    tenantRoles: TenantRole[];
    tenantUsers: TenantUser[];
}

async function loadSecuritySnapshot(tenantId: string): Promise<SecuritySnapshot> {
    const [tenant, currentUser, tenantRoles, tenantUsers] = await Promise.all([
        getCurrentTenant(),
        getCurrentUser(tenantId),
        getTenantRoles(),
        getTenantUsers(),
    ]);

    return {
        tenant,
        currentUser,
        tenantRoles,
        tenantUsers,
    };
}

function getErrorMessage(error: unknown, fallback: string): string {
    const response = error as {
        response?: {
            data?: {
                detail?: unknown;
            };
        };
    };

    if (
        typeof response.response?.data?.detail === "string" &&
        response.response.data.detail.trim().length > 0
    ) {
        return response.response.data.detail;
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return fallback;
}

function displayName(user: Pick<CurrentUserResponse, "full_name" | "email">): string {
    return user.full_name?.trim() || user.email;
}

function statusTone(active: boolean): string {
    return active
        ? "bg-emerald-100 text-emerald-800"
        : "bg-amber-100 text-amber-900";
}

function permissionTone(permissionCode: string): string {
    if (permissionCode === "tenant.admin") {
        return "bg-amber-100 text-amber-900";
    }
    if (permissionCode.startsWith("billing.")) {
        return "bg-sky-100 text-sky-800";
    }
    return "bg-slate-100 text-slate-700";
}

function SectionCard({
    title,
    body,
    children,
}: {
    title: string;
    body?: string;
    children: React.ReactNode;
}) {
    return (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-2">
                <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
                {body ? (
                    <p className="text-sm text-slate-600">{body}</p>
                ) : null}
            </div>
            <div className="mt-5">{children}</div>
        </section>
    );
}

function DetailItem({
    label,
    value,
    subdued = false,
}: {
    label: string;
    value: React.ReactNode;
    subdued?: boolean;
}) {
    return (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                {label}
            </p>
            <div
                className={`mt-1 text-sm ${
                    subdued ? "text-slate-600" : "font-medium text-slate-900"
                }`}
            >
                {value}
            </div>
        </div>
    );
}

function StatusBadge({
    children,
    active,
}: {
    children: React.ReactNode;
    active: boolean;
}) {
    return (
        <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${statusTone(active)}`}
        >
            {children}
        </span>
    );
}

function RoleBadge({ roleName }: { roleName: string }) {
    const ownerTone =
        roleName === "owner"
            ? "bg-amber-100 text-amber-900"
            : "bg-slate-100 text-slate-700";

    return (
        <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${ownerTone}`}
        >
            {roleName}
        </span>
    );
}

function PermissionBadge({ permissionCode }: { permissionCode: string }) {
    return (
        <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${permissionTone(permissionCode)}`}
        >
            {permissionCode}
        </span>
    );
}

export default function SecuritySettingsPage() {
    const auth = useAuth();
    const [snapshot, setSnapshot] = useState<SecuritySnapshot | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [loadError, setLoadError] = useState<string>("");
    const [actionError, setActionError] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [isRequestingReset, setIsRequestingReset] = useState<boolean>(false);

    async function loadSecurityState(tenantId: string): Promise<void> {
        if (!tenantId) {
            setLoadError("Authenticated tenant context is unavailable.");
            setIsLoading(false);
            return;
        }

        try {
            setIsLoading(true);
            setLoadError("");
            setSnapshot(await loadSecuritySnapshot(tenantId));
        } catch (error) {
            setLoadError(
                getErrorMessage(
                    error,
                    "Unable to load the current security configuration.",
                ),
            );
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        void loadSecurityState(auth.user?.tenant_id ?? "");
    }, [auth.isReady, auth.user?.tenant_id]);

    async function handlePasswordResetRequest(): Promise<void> {
        if (!snapshot) {
            return;
        }

        try {
            setIsRequestingReset(true);
            setActionError("");
            setSuccessMessage("");
            const response = await requestPasswordReset({
                tenant_id: snapshot.tenant.id,
                email: snapshot.currentUser.email,
            });
            setSuccessMessage(response.message);
        } catch (error) {
            setActionError(
                getErrorMessage(error, "Unable to request password reset instructions."),
            );
        } finally {
            setIsRequestingReset(false);
        }
    }

    if (isLoading) {
        return (
            <div className="space-y-6">
                <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-semibold text-slate-900">
                        Loading security settings
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Gathering the current account, RBAC, and tenant-access posture for this tenant.
                    </p>
                </section>
            </div>
        );
    }

    if (loadError || !snapshot) {
        return (
            <section className="rounded-xl border border-red-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-900">
                    Unable to load security settings
                </h2>
                <p className="mt-2 text-sm text-slate-600">
                    {loadError || "Security state could not be resolved."}
                </p>
                <button
                    type="button"
                    onClick={() => {
                        void loadSecurityState(auth.user?.tenant_id ?? "");
                    }}
                    className="mt-4 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                    Retry
                </button>
            </section>
        );
    }

    const { currentUser, tenant, tenantRoles, tenantUsers } = snapshot;
    const currentRoleNames = [...currentUser.roles];
    if (currentUser.is_owner && !currentRoleNames.includes("owner")) {
        currentRoleNames.unshift("owner");
    }

    const effectivePermissionCodes = Array.from(
        new Set(
            tenantRoles
                .filter((role) => currentRoleNames.includes(role.name))
                .flatMap((role) => role.permission_codes),
        ),
    ).sort((left, right) => left.localeCompare(right));

    const activeOwnerCount = tenantUsers.filter(
        (user) => user.user_is_active && user.membership_is_active && user.is_owner,
    ).length;
    const adminCoverageCount = tenantUsers.filter(
        (user) =>
            user.user_is_active &&
            user.membership_is_active &&
            (user.is_owner || user.role_names.includes("admin")),
    ).length;
    const inactiveMembershipCount = tenantUsers.filter(
        (user) => !user.user_is_active || !user.membership_is_active,
    ).length;

    return (
        <div className="space-y-6">
            {successMessage ? (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                    {successMessage}
                </div>
            ) : null}
            {actionError ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {actionError}
                </div>
            ) : null}

            <SectionCard
                title="Account security"
                body="Review the current authenticated account, tenant context, and the status checks that keep this admin session valid."
            >
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <DetailItem
                        label="Current account"
                        value={
                            <div>
                                <p>{displayName(currentUser)}</p>
                                <p className="mt-1 text-xs text-slate-500">
                                    {currentUser.email}
                                </p>
                            </div>
                        }
                    />
                    <DetailItem
                        label="Current tenant"
                        value={
                            <div>
                                <p>{tenant.name}</p>
                                <p className="mt-1 text-xs text-slate-500">{tenant.id}</p>
                            </div>
                        }
                    />
                    <DetailItem
                        label="Membership summary"
                        value={
                            <div className="flex flex-wrap gap-2">
                                <StatusBadge
                                    active={currentUser.membership_is_active}
                                >
                                    {currentUser.membership_is_active
                                        ? "Active membership"
                                        : "Membership inactive"}
                                </StatusBadge>
                                <StatusBadge active={currentUser.is_owner}>
                                    {currentUser.is_owner ? "Owner" : "Non-owner"}
                                </StatusBadge>
                            </div>
                        }
                    />
                    <DetailItem
                        label="Account status"
                        value={
                            <div className="flex flex-wrap gap-2">
                                <StatusBadge active={tenant.is_active}>
                                    {tenant.is_active ? "Tenant active" : "Tenant inactive"}
                                </StatusBadge>
                                <StatusBadge active={currentUser.user_is_active}>
                                    {currentUser.user_is_active
                                        ? "User active"
                                        : "User inactive"}
                                </StatusBadge>
                            </div>
                        }
                    />
                </div>
            </SectionCard>

            <div className="grid gap-6 xl:grid-cols-[1.2fr,1fr]">
                <SectionCard
                    title="Access & permissions"
                    body="Current role assignments come from tenant membership plus tenant role bindings. The permission list below is derived from the tenant role catalog already seeded in SupaCRM."
                >
                    <div className="space-y-5">
                        <div>
                            <h3 className="text-sm font-semibold text-slate-900">
                                Current access
                            </h3>
                            <div className="mt-3 flex flex-wrap gap-2">
                                {currentRoleNames.length > 0 ? (
                                    currentRoleNames.map((roleName) => (
                                        <RoleBadge
                                            key={roleName}
                                            roleName={roleName}
                                        />
                                    ))
                                ) : (
                                    <p className="text-sm text-slate-600">
                                        No tenant roles are currently assigned.
                                    </p>
                                )}
                            </div>
                        </div>

                        <div>
                            <h3 className="text-sm font-semibold text-slate-900">
                                Effective permissions
                            </h3>
                            {effectivePermissionCodes.length > 0 ? (
                                <div className="mt-3 space-y-3">
                                    <div className="flex flex-wrap gap-2">
                                        {effectivePermissionCodes.map((permissionCode) => (
                                            <PermissionBadge
                                                key={permissionCode}
                                                permissionCode={permissionCode}
                                            />
                                        ))}
                                    </div>
                                    <div className="grid gap-3 md:grid-cols-2">
                                        {effectivePermissionCodes.map((permissionCode) => (
                                            <DetailItem
                                                key={permissionCode}
                                                label={permissionCode}
                                                value={describePermission(permissionCode)}
                                                subdued
                                            />
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <p className="mt-3 text-sm text-slate-600">
                                    No effective permissions were resolved from the current tenant roles.
                                </p>
                            )}
                        </div>
                    </div>
                </SectionCard>

                <SectionCard
                    title="Tenant role catalog"
                    body="Each tenant role below is backed by the current RBAC seed definitions and the live role-permission assignments returned by the tenant APIs."
                >
                    <div className="space-y-4">
                        {tenantRoles.map((role) => (
                            <article
                                key={role.id}
                                className="rounded-xl border border-slate-200 p-4"
                            >
                                <div className="flex flex-wrap items-center gap-2">
                                    <RoleBadge roleName={role.name} />
                                    <span className="text-xs text-slate-500">
                                        {role.permission_codes.length} permissions
                                    </span>
                                </div>
                                <p className="mt-2 text-sm text-slate-600">
                                    {describeRole(role.name)}
                                </p>
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {role.permission_codes.map((permissionCode) => (
                                        <PermissionBadge
                                            key={`${role.id}-${permissionCode}`}
                                            permissionCode={permissionCode}
                                        />
                                    ))}
                                </div>
                            </article>
                        ))}
                    </div>
                </SectionCard>
            </div>

            <div className="grid gap-6 xl:grid-cols-2">
                <SectionCard
                    title="Session / auth state"
                    body="These controls and indicators reflect the current browser session and the auth lifecycle already present in SupaCRM."
                >
                    <div className="grid gap-4 md:grid-cols-2">
                        <DetailItem
                            label="Bearer session"
                            value={auth.accessToken ? "Access token present" : "Access token missing"}
                        />
                        <DetailItem
                            label="Session renewal"
                            value={
                                auth.refreshToken
                                    ? "Refresh token available for automatic renewal"
                                    : "No refresh token is available"
                            }
                            subdued
                        />
                        <DetailItem
                            label="Tenant binding"
                            value="Protected requests include the tenant header for this session."
                            subdued
                        />
                        <DetailItem
                            label="Current action"
                            value={
                                <div className="flex flex-wrap items-center gap-3">
                                    <span className="text-sm text-slate-600">
                                        End this browser session cleanly.
                                    </span>
                                    <LogoutButton />
                                </div>
                            }
                        />
                    </div>
                </SectionCard>

                <SectionCard
                    title="Password / recovery"
                    body="SupaCRM already supports password reset request and confirm flows. This page only exposes the supported request entrypoint; password changes still complete through the reset token flow."
                >
                    <div className="space-y-4">
                        <DetailItem
                            label="Recovery target"
                            value={currentUser.email}
                        />
                        <DetailItem
                            label="Supported flow"
                            value="Request reset instructions for the current account using the existing auth route."
                            subdued
                        />
                        <div className="flex flex-wrap items-center gap-3">
                            <button
                                type="button"
                                onClick={() => {
                                    void handlePasswordResetRequest();
                                }}
                                disabled={isRequestingReset}
                                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                {isRequestingReset
                                    ? "Requesting reset..."
                                    : "Request reset instructions"}
                            </button>
                            <p className="text-sm text-slate-500">
                                No in-app password change form is exposed in this slice.
                            </p>
                        </div>
                    </div>
                </SectionCard>
            </div>

            <SectionCard
                title="Tenant security posture"
                body="This operational view summarizes the tenant access model and the safeguards already enforced by the current SupaCRM tenancy and auth layers."
            >
                <div className="grid gap-4 md:grid-cols-3">
                    <DetailItem
                        label="Active owners"
                        value={String(activeOwnerCount)}
                        subdued
                    />
                    <DetailItem
                        label="Admin-capable members"
                        value={String(adminCoverageCount)}
                        subdued
                    />
                    <DetailItem
                        label="Inactive memberships"
                        value={String(inactiveMembershipCount)}
                        subdued
                    />
                </div>

                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                    {TENANT_SECURITY_SAFEGUARDS.map((item) => (
                        <article
                            key={item.title}
                            className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                        >
                            <h3 className="text-sm font-semibold text-slate-900">
                                {item.title}
                            </h3>
                            <p className="mt-2 text-sm text-slate-600">{item.body}</p>
                        </article>
                    ))}
                </div>
            </SectionCard>
        </div>
    );
}

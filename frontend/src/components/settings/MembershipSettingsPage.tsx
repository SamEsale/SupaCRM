"use client";

import { useEffect, useMemo, useState } from "react";

import {
    getTenantUsers,
    removeTenantMembership,
    updateTenantMembership,
} from "@/services/tenants.service";
import type { TenantUser } from "@/types/tenants";

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

function formatDate(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }

    return parsed.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
    });
}

function sortRoleNames(roleNames: string[]): string[] {
    return [...roleNames].sort((left, right) => left.localeCompare(right));
}

function hasAdminCoverage(user: TenantUser): boolean {
    return user.user_is_active && user.membership_is_active && (user.is_owner || user.role_names.includes("admin"));
}

function membershipStateLabel(user: TenantUser): string {
    if (!user.user_is_active) {
        return "User disabled";
    }
    if (!user.membership_is_active) {
        return "Membership inactive";
    }
    return "Active";
}

function displayName(user: TenantUser): string {
    return user.full_name?.trim() || user.email;
}

function StatusBadge({ user }: { user: TenantUser }) {
    const active = user.user_is_active && user.membership_is_active;

    return (
        <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                active
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-900"
            }`}
        >
            {membershipStateLabel(user)}
        </span>
    );
}

function RoleBadge({
    children,
    tone = "neutral",
}: {
    children: React.ReactNode;
    tone?: "neutral" | "owner";
}) {
    return (
        <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                tone === "owner"
                    ? "bg-amber-100 text-amber-900"
                    : "bg-slate-100 text-slate-700"
            }`}
        >
            {children}
        </span>
    );
}

export default function MembershipSettingsPage() {
    const [members, setMembers] = useState<TenantUser[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [loadError, setLoadError] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [actionError, setActionError] = useState<string>("");
    const [pendingUserId, setPendingUserId] = useState<string>("");
    const [selectedTransferTargetUserId, setSelectedTransferTargetUserId] = useState<string>("");
    const [selectedTransferSourceUserId, setSelectedTransferSourceUserId] = useState<string>("");
    const [isSubmittingTransfer, setIsSubmittingTransfer] = useState<boolean>(false);

    async function loadMembers(): Promise<void> {
        try {
            setIsLoading(true);
            setLoadError("");
            const users = await getTenantUsers();
            setMembers(users);
        } catch (error) {
            setLoadError(getErrorMessage(error, "Failed to load tenant membership."));
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        void loadMembers();
    }, []);

    const activeMembers = useMemo(
        () => members.filter((member) => member.user_is_active && member.membership_is_active),
        [members],
    );
    const inactiveMembers = members.length - activeMembers.length;
    const ownerMembers = useMemo(
        () => members.filter((member) => member.is_owner),
        [members],
    );
    const activeOwners = useMemo(
        () => members.filter((member) => member.user_is_active && member.membership_is_active && member.is_owner),
        [members],
    );
    const transferCandidates = useMemo(
        () => members.filter((member) => member.user_is_active && member.membership_is_active && !member.is_owner),
        [members],
    );

    useEffect(() => {
        if (transferCandidates.length === 0) {
            setSelectedTransferTargetUserId("");
            return;
        }

        const candidateStillExists = transferCandidates.some(
            (member) => member.user_id === selectedTransferTargetUserId,
        );
        if (!candidateStillExists) {
            setSelectedTransferTargetUserId(transferCandidates[0].user_id);
        }
    }, [selectedTransferTargetUserId, transferCandidates]);

    useEffect(() => {
        if (activeOwners.length === 0) {
            setSelectedTransferSourceUserId("");
            return;
        }

        const sourceStillExists = activeOwners.some(
            (member) => member.user_id === selectedTransferSourceUserId,
        );
        if (!sourceStillExists) {
            setSelectedTransferSourceUserId(activeOwners[0].user_id);
        }
    }, [activeOwners, selectedTransferSourceUserId]);

    async function refreshMembers(): Promise<void> {
        const users = await getTenantUsers();
        setMembers(users);
    }

    function resetFeedback(): void {
        setSuccessMessage("");
        setActionError("");
    }

    async function handleDeactivate(member: TenantUser): Promise<void> {
        const confirmed = window.confirm(
            `Deactivate ${displayName(member)}? They will immediately lose tenant access.`,
        );
        if (!confirmed) {
            return;
        }

        try {
            resetFeedback();
            setPendingUserId(member.user_id);
            await updateTenantMembership(member.user_id, {
                membership_is_active: false,
            });
            await refreshMembers();
            setSuccessMessage(`Membership deactivated for ${member.email}.`);
        } catch (error) {
            setActionError(getErrorMessage(error, "Failed to deactivate membership."));
        } finally {
            setPendingUserId("");
        }
    }

    async function handleReactivate(member: TenantUser): Promise<void> {
        try {
            resetFeedback();
            setPendingUserId(member.user_id);
            await updateTenantMembership(member.user_id, {
                membership_is_active: true,
            });
            await refreshMembers();
            setSuccessMessage(`Membership reactivated for ${member.email}.`);
        } catch (error) {
            setActionError(getErrorMessage(error, "Failed to reactivate membership."));
        } finally {
            setPendingUserId("");
        }
    }

    async function handleRemove(member: TenantUser): Promise<void> {
        const confirmed = window.confirm(
            `Remove ${displayName(member)} from this tenant? This removes their membership and tenant role assignments.`,
        );
        if (!confirmed) {
            return;
        }

        try {
            resetFeedback();
            setPendingUserId(member.user_id);
            await removeTenantMembership(member.user_id);
            await refreshMembers();
            setSuccessMessage(`Membership removed for ${member.email}.`);
        } catch (error) {
            setActionError(getErrorMessage(error, "Failed to remove member from tenant."));
        } finally {
            setPendingUserId("");
        }
    }

    async function handleGrantOwner(member: TenantUser): Promise<void> {
        const confirmed = window.confirm(
            `Grant owner access to ${displayName(member)}? This keeps existing owners in place.`,
        );
        if (!confirmed) {
            return;
        }

        try {
            resetFeedback();
            setPendingUserId(member.user_id);
            await updateTenantMembership(member.user_id, {
                is_owner: true,
            });
            await refreshMembers();
            setSuccessMessage(`Owner access granted to ${member.email}.`);
        } catch (error) {
            setActionError(getErrorMessage(error, "Failed to grant owner access."));
        } finally {
            setPendingUserId("");
        }
    }

    async function handleTransferOwnership(
        event: React.FormEvent<HTMLFormElement>,
    ): Promise<void> {
        event.preventDefault();
        resetFeedback();

        if (!selectedTransferTargetUserId || !selectedTransferSourceUserId) {
            setActionError("Select both the current owner and the next owner before transferring.");
            return;
        }

        const sourceMember = members.find((member) => member.user_id === selectedTransferSourceUserId);
        const targetMember = members.find((member) => member.user_id === selectedTransferTargetUserId);
        if (!sourceMember || !targetMember) {
            setActionError("Refresh the membership list and retry the ownership transfer.");
            return;
        }

        const confirmed = window.confirm(
            `Transfer ownership from ${displayName(sourceMember)} to ${displayName(targetMember)}?`,
        );
        if (!confirmed) {
            return;
        }

        try {
            setIsSubmittingTransfer(true);
            await updateTenantMembership(targetMember.user_id, {
                is_owner: true,
                transfer_owner_from_user_id: sourceMember.user_id,
            });
            await refreshMembers();
            setSuccessMessage(
                `Ownership transferred from ${sourceMember.email} to ${targetMember.email}.`,
            );
        } catch (error) {
            setActionError(getErrorMessage(error, "Failed to transfer ownership."));
        } finally {
            setIsSubmittingTransfer(false);
        }
    }

    return (
        <div className="space-y-6">
            <section className="grid gap-4 md:grid-cols-4">
                <SummaryCard label="Members" value={String(members.length)} />
                <SummaryCard label="Active" value={String(activeMembers.length)} />
                <SummaryCard label="Inactive" value={String(inactiveMembers)} />
                <SummaryCard label="Owners" value={String(ownerMembers.length)} />
            </section>

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

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <p className="text-sm text-slate-600">Loading tenant membership...</p>
                </section>
            ) : null}

            {!isLoading && loadError ? (
                <section className="rounded-xl border border-red-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-semibold text-slate-900">
                        Unable to load membership
                    </h2>
                    <p className="mt-2 text-sm text-red-700">{loadError}</p>
                    <button
                        type="button"
                        onClick={() => void loadMembers()}
                        className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                    >
                        Retry
                    </button>
                </section>
            ) : null}

            {!isLoading && !loadError ? (
                <section className="grid gap-6 xl:grid-cols-[1.8fr_1fr]">
                    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
                        <div className="border-b border-slate-200 px-6 py-5">
                            <h2 className="text-xl font-semibold text-slate-900">
                                Tenant membership
                            </h2>
                            <p className="mt-1 text-sm text-slate-600">
                                Manage access state, remove stale memberships, and review owner coverage across the current tenant.
                            </p>
                        </div>

                        {members.length === 0 ? (
                            <div className="px-6 py-10 text-sm text-slate-600">
                                No tenant members were found. Add a user in Settings / Users before managing membership lifecycle.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-slate-200">
                                    <thead className="bg-slate-50">
                                        <tr className="text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                                            <th className="px-6 py-3">Member</th>
                                            <th className="px-6 py-3">Membership</th>
                                            <th className="px-6 py-3">Owner</th>
                                            <th className="px-6 py-3">Roles</th>
                                            <th className="px-6 py-3">Access</th>
                                            <th className="px-6 py-3">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 bg-white">
                                        {members.map((member) => {
                                            const isPending = pendingUserId === member.user_id;

                                            return (
                                                <tr key={member.user_id}>
                                                    <td className="px-6 py-4">
                                                        <p className="font-medium text-slate-900">
                                                            {displayName(member)}
                                                        </p>
                                                        <p className="mt-1 text-sm text-slate-500">
                                                            {member.email}
                                                        </p>
                                                        <p className="mt-1 text-xs text-slate-400">
                                                            Member since {formatDate(member.membership_created_at)}
                                                        </p>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <StatusBadge user={member} />
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        {member.is_owner ? (
                                                            <RoleBadge tone="owner">Owner</RoleBadge>
                                                        ) : (
                                                            <span className="text-sm text-slate-500">
                                                                Standard
                                                            </span>
                                                        )}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="flex flex-wrap gap-2">
                                                            {member.role_names.length > 0 ? (
                                                                sortRoleNames(member.role_names).map((roleName) => (
                                                                    <RoleBadge key={`${member.user_id}-${roleName}`}>
                                                                        {roleName}
                                                                    </RoleBadge>
                                                                ))
                                                            ) : (
                                                                <span className="text-sm text-slate-500">
                                                                    No roles assigned
                                                                </span>
                                                            )}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span
                                                            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                                                                hasAdminCoverage(member)
                                                                    ? "bg-slate-900 text-white"
                                                                    : "bg-slate-100 text-slate-600"
                                                            }`}
                                                        >
                                                            {hasAdminCoverage(member)
                                                                ? "Admin coverage"
                                                                : "Standard access"}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="flex flex-wrap gap-2">
                                                            {member.membership_is_active ? (
                                                                <button
                                                                    type="button"
                                                                    disabled={isPending}
                                                                    onClick={() => void handleDeactivate(member)}
                                                                    className="rounded-lg border border-amber-300 px-3 py-2 text-sm font-medium text-amber-800 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60"
                                                                >
                                                                    Deactivate
                                                                </button>
                                                            ) : (
                                                                <button
                                                                    type="button"
                                                                    disabled={isPending}
                                                                    onClick={() => void handleReactivate(member)}
                                                                    className="rounded-lg border border-emerald-300 px-3 py-2 text-sm font-medium text-emerald-800 transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                                                                >
                                                                    Reactivate
                                                                </button>
                                                            )}

                                                            {!member.is_owner && member.user_is_active && member.membership_is_active ? (
                                                                <button
                                                                    type="button"
                                                                    disabled={isPending}
                                                                    onClick={() => void handleGrantOwner(member)}
                                                                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                                                                >
                                                                    Grant owner
                                                                </button>
                                                            ) : null}

                                                            <button
                                                                type="button"
                                                                disabled={isPending}
                                                                onClick={() => void handleRemove(member)}
                                                                className="rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                                                            >
                                                                Remove
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>

                    <div className="space-y-6">
                        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <h2 className="text-lg font-semibold text-slate-900">
                                Ownership transfer
                            </h2>
                            <p className="mt-1 text-sm text-slate-600">
                                Move primary owner responsibility to another active tenant member without leaving the tenant ownerless.
                            </p>

                            <div className="mt-4 space-y-3">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                                        Active owners
                                    </p>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {activeOwners.length > 0 ? (
                                            activeOwners.map((member) => (
                                                <RoleBadge key={member.user_id} tone="owner">
                                                    {displayName(member)}
                                                </RoleBadge>
                                            ))
                                        ) : (
                                            <span className="text-sm text-slate-500">
                                                No active owners currently available.
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {activeOwners.length > 0 && transferCandidates.length > 0 ? (
                                <form className="mt-5 space-y-4" onSubmit={handleTransferOwnership}>
                                    <div>
                                        <label
                                            htmlFor="membership-transfer-source"
                                            className="mb-1 block text-sm font-medium text-slate-700"
                                        >
                                            Transfer from
                                        </label>
                                        <select
                                            id="membership-transfer-source"
                                            value={selectedTransferSourceUserId}
                                            onChange={(event) =>
                                                setSelectedTransferSourceUserId(event.target.value)
                                            }
                                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                        >
                                            {activeOwners.map((member) => (
                                                <option key={member.user_id} value={member.user_id}>
                                                    {displayName(member)}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <div>
                                        <label
                                            htmlFor="membership-transfer-target"
                                            className="mb-1 block text-sm font-medium text-slate-700"
                                        >
                                            Transfer to
                                        </label>
                                        <select
                                            id="membership-transfer-target"
                                            value={selectedTransferTargetUserId}
                                            onChange={(event) =>
                                                setSelectedTransferTargetUserId(event.target.value)
                                            }
                                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                        >
                                            {transferCandidates.map((member) => (
                                                <option key={member.user_id} value={member.user_id}>
                                                    {displayName(member)}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <button
                                        type="submit"
                                        disabled={isSubmittingTransfer}
                                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {isSubmittingTransfer ? "Transferring..." : "Transfer ownership"}
                                    </button>
                                </form>
                            ) : (
                                <p className="mt-4 text-sm text-slate-600">
                                    Ownership transfer becomes available when the tenant has at least one active owner and one separate active non-owner member.
                                </p>
                            )}
                        </section>

                        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                            <h2 className="text-lg font-semibold text-slate-900">
                                Access safeguards
                            </h2>
                            <ul className="mt-3 space-y-2 text-sm text-slate-600">
                                <li>Last active owners cannot be removed or deactivated.</li>
                                <li>Tenant admin coverage cannot be reduced to zero by lifecycle mutations.</li>
                                <li>Owner transfers only target active members in the current tenant.</li>
                            </ul>
                        </section>
                    </div>
                </section>
            ) : null}
        </div>
    );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                {label}
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p>
        </div>
    );
}

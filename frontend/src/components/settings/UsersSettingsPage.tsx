"use client";

import { useEffect, useState } from "react";

import {
    assignTenantUserRoles,
    createTenantUser,
    getTenantRoles,
    getTenantUsers,
} from "@/services/tenants.service";
import type {
    TenantRole,
    TenantUser,
    TenantUserProvisionRequest,
} from "@/types/tenants";

const initialCreateForm: TenantUserProvisionRequest = {
    email: "",
    full_name: "",
    password: "",
    role_names: ["user"],
    is_owner: false,
};

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

function formatMembershipState(user: TenantUser): string {
    if (!user.user_is_active) {
        return "User disabled";
    }
    if (!user.membership_is_active) {
        return "Membership inactive";
    }
    return "Active";
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

function RoleBadge({
    roleName,
    tone = "neutral",
}: {
    roleName: string;
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
            {roleName}
        </span>
    );
}

function StatusBadge({ user }: { user: TenantUser }) {
    const state = formatMembershipState(user);
    const className = user.user_is_active && user.membership_is_active
        ? "bg-emerald-100 text-emerald-800"
        : "bg-amber-100 text-amber-900";

    return (
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${className}`}>
            {state}
        </span>
    );
}

export default function UsersSettingsPage() {
    const [users, setUsers] = useState<TenantUser[]>([]);
    const [roles, setRoles] = useState<TenantRole[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [loadError, setLoadError] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [createError, setCreateError] = useState<string>("");
    const [assignmentError, setAssignmentError] = useState<string>("");
    const [isCreatingUser, setIsCreatingUser] = useState<boolean>(false);
    const [isSavingAccess, setIsSavingAccess] = useState<boolean>(false);
    const [createForm, setCreateForm] =
        useState<TenantUserProvisionRequest>(initialCreateForm);
    const [selectedUserId, setSelectedUserId] = useState<string>("");
    const [additionalRoleName, setAdditionalRoleName] = useState<string>("");
    const [promoteToOwner, setPromoteToOwner] = useState<boolean>(false);

    async function loadData(): Promise<void> {
        try {
            setIsLoading(true);
            setLoadError("");
            const [usersResponse, rolesResponse] = await Promise.all([
                getTenantUsers(),
                getTenantRoles(),
            ]);
            setUsers(usersResponse);
            setRoles(rolesResponse);
        } catch (error) {
            setLoadError(
                getErrorMessage(
                    error,
                    "Failed to load tenant users and roles.",
                ),
            );
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        void loadData();
    }, []);

    const selectedUser =
        users.find((candidate) => candidate.user_id === selectedUserId) ?? users[0] ?? null;

    useEffect(() => {
        if (users.length === 0) {
            setSelectedUserId("");
            setAdditionalRoleName("");
            setPromoteToOwner(false);
            return;
        }

        const hasSelectedUser = users.some(
            (candidate) => candidate.user_id === selectedUserId,
        );
        if (!hasSelectedUser) {
            setSelectedUserId(users[0].user_id);
        }
    }, [selectedUserId, users]);

    useEffect(() => {
        if (!selectedUser) {
            setAdditionalRoleName("");
            setPromoteToOwner(false);
            return;
        }

        setAdditionalRoleName("");
        setPromoteToOwner(selectedUser.is_owner);
    }, [selectedUser]);

    const availableAdditionalRoles = selectedUser
        ? roles.filter((role) => !selectedUser.role_names.includes(role.name))
        : [];
    const usersTotal = users.length;
    const activeUsersTotal = users.filter(
        (user) => user.user_is_active && user.membership_is_active,
    ).length;
    const ownersTotal = users.filter((user) => user.is_owner).length;

    function resetFeedback(): void {
        setSuccessMessage("");
        setCreateError("");
        setAssignmentError("");
    }

    function toggleCreateRole(roleName: string, checked: boolean): void {
        setCreateForm((current) => {
            const nextRoleNames = checked
                ? sortRoleNames([...new Set([...current.role_names, roleName])])
                : current.role_names.filter((role) => role !== roleName);

            return {
                ...current,
                role_names: nextRoleNames,
            };
        });
    }

    function handleSelectedUserChange(userId: string): void {
        const nextUser = users.find((candidate) => candidate.user_id === userId);
        if (!nextUser) {
            return;
        }

        setSelectedUserId(nextUser.user_id);
        setAdditionalRoleName("");
        setPromoteToOwner(nextUser.is_owner);
        setAssignmentError("");
        setSuccessMessage("");
    }

    async function refreshUsers(): Promise<void> {
        const refreshedUsers = await getTenantUsers();
        setUsers(refreshedUsers);
    }

    async function handleCreateUser(
        event: React.FormEvent<HTMLFormElement>,
    ): Promise<void> {
        event.preventDefault();
        resetFeedback();

        if (createForm.role_names.length === 0) {
            setCreateError("Select at least one role for the new user.");
            return;
        }

        try {
            setIsCreatingUser(true);
            const created = await createTenantUser({
                ...createForm,
                email: createForm.email.trim(),
                full_name: createForm.full_name?.trim() || null,
                password: createForm.password?.trim() || null,
                role_names: createForm.role_names,
                is_owner: createForm.is_owner,
            });
            await refreshUsers();
            setCreateForm(initialCreateForm);
            setSuccessMessage(`User ${created.email} added successfully.`);
        } catch (error) {
            setCreateError(
                getErrorMessage(error, "Failed to create tenant user."),
            );
        } finally {
            setIsCreatingUser(false);
        }
    }

    async function handleAssignRoles(
        event: React.FormEvent<HTMLFormElement>,
    ): Promise<void> {
        event.preventDefault();
        resetFeedback();

        if (!selectedUser) {
            setAssignmentError("Select a user before managing access.");
            return;
        }

        const nextRoleNames = sortRoleNames([
            ...new Set([
                ...selectedUser.role_names,
                ...(additionalRoleName ? [additionalRoleName] : []),
            ]),
        ]);

        if (nextRoleNames.length === 0 && !promoteToOwner) {
            setAssignmentError("Select an additional role or enable owner access.");
            return;
        }

        try {
            setIsSavingAccess(true);
            await assignTenantUserRoles(selectedUser.user_id, {
                role_names: nextRoleNames.length > 0 ? nextRoleNames : ["owner"],
                is_owner: promoteToOwner,
            });
            await refreshUsers();
            setAdditionalRoleName("");
            setSuccessMessage(`Access updated for ${selectedUser.email}.`);
        } catch (error) {
            setAssignmentError(
                getErrorMessage(error, "Failed to update user access."),
            );
        } finally {
            setIsSavingAccess(false);
        }
    }

    return (
        <div className="space-y-6">
            <section className="grid gap-4 md:grid-cols-3">
                <SummaryCard label="Users" value={String(usersTotal)} />
                <SummaryCard label="Active members" value={String(activeUsersTotal)} />
                <SummaryCard label="Owners" value={String(ownersTotal)} />
            </section>

            {successMessage ? (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                    {successMessage}
                </div>
            ) : null}

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <p className="text-sm text-slate-600">Loading tenant users...</p>
                </section>
            ) : null}

            {!isLoading && loadError ? (
                <section className="rounded-xl border border-red-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-semibold text-slate-900">
                        Unable to load users
                    </h2>
                    <p className="mt-2 text-sm text-red-700">{loadError}</p>
                    <button
                        type="button"
                        onClick={() => void loadData()}
                        className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                    >
                        Retry
                    </button>
                </section>
            ) : null}

            {!isLoading && !loadError ? (
                <div className="mx-auto max-w-5xl space-y-6">
                    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
                        <div className="border-b border-slate-200 px-6 py-5">
                            <h2 className="text-xl font-semibold text-slate-900">
                                Tenant users
                            </h2>
                            <p className="mt-1 text-sm text-slate-600">
                                Review active access, owner coverage, and assigned roles across the current tenant.
                            </p>
                        </div>

                        {users.length === 0 ? (
                            <div className="px-6 py-10 text-sm text-slate-600">
                                No tenant users exist yet. Add the first operator below.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-slate-200">
                                    <thead className="bg-slate-50">
                                        <tr className="text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                                            <th className="px-6 py-3">User</th>
                                            <th className="px-6 py-3">State</th>
                                            <th className="px-6 py-3">Owner</th>
                                            <th className="px-6 py-3">Roles</th>
                                            <th className="px-6 py-3">Member since</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 bg-white">
                                        {users.map((user) => (
                                            <tr
                                                key={user.user_id}
                                                className={`transition ${
                                                    selectedUserId === user.user_id
                                                        ? "bg-slate-50"
                                                        : ""
                                                }`}
                                            >
                                                <td className="px-6 py-4">
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            handleSelectedUserChange(user.user_id)
                                                        }
                                                        className="text-left"
                                                    >
                                                        <p className="font-medium text-slate-900">
                                                            {user.full_name?.trim() || user.email}
                                                        </p>
                                                        {user.full_name?.trim() ? (
                                                            <p className="mt-1 text-sm text-slate-500">
                                                                {user.email}
                                                            </p>
                                                        ) : null}
                                                    </button>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <StatusBadge user={user} />
                                                </td>
                                                <td className="px-6 py-4">
                                                    {user.is_owner ? (
                                                        <RoleBadge roleName="Owner" tone="owner" />
                                                    ) : (
                                                        <span className="text-sm text-slate-500">
                                                            Standard
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex flex-wrap gap-2">
                                                        {user.role_names.length > 0 ? (
                                                            sortRoleNames(user.role_names).map((roleName) => (
                                                                <RoleBadge
                                                                    key={`${user.user_id}-${roleName}`}
                                                                    roleName={roleName}
                                                                />
                                                            ))
                                                        ) : (
                                                            <span className="text-sm text-slate-500">
                                                                No roles assigned
                                                            </span>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-sm text-slate-500">
                                                    {formatDate(user.membership_created_at)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h2 className="text-lg font-semibold text-slate-900">
                            Manage roles
                        </h2>
                        <p className="mt-1 text-sm text-slate-600">
                            Grant additional tenant roles and owner access using the existing role-assignment route. Existing roles remain in place in this slice.
                        </p>

                        {selectedUser ? (
                            <form className="mt-5 space-y-4" onSubmit={handleAssignRoles}>
                                <div>
                                    <label
                                        htmlFor="settings-selected-user"
                                        className="mb-1 block text-sm font-medium text-slate-700"
                                    >
                                        Selected user
                                    </label>
                                    <select
                                        id="settings-selected-user"
                                        value={selectedUser.user_id}
                                        onChange={(event) =>
                                            handleSelectedUserChange(event.target.value)
                                        }
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                    >
                                        {users.map((user) => (
                                            <option key={user.user_id} value={user.user_id}>
                                                {user.full_name?.trim() || user.email}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <p className="text-sm font-medium text-slate-700">
                                        Current roles
                                    </p>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {selectedUser.role_names.length > 0 ? (
                                            sortRoleNames(selectedUser.role_names).map((roleName) => (
                                                <RoleBadge
                                                    key={`${selectedUser.user_id}-${roleName}`}
                                                    roleName={roleName}
                                                />
                                            ))
                                        ) : (
                                            <span className="text-sm text-slate-500">
                                                No roles assigned yet
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div>
                                    <p className="mb-1 text-sm font-medium text-slate-700">
                                        Additional role
                                    </p>
                                    {availableAdditionalRoles.length > 0 ? (
                                        <div className="flex flex-wrap gap-2">
                                            {availableAdditionalRoles.map((role) => {
                                                const isSelected =
                                                    additionalRoleName === role.name;

                                                return (
                                                    <button
                                                        key={role.id}
                                                        type="button"
                                                        onClick={() =>
                                                            setAdditionalRoleName(role.name)
                                                        }
                                                        className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
                                                            isSelected
                                                                ? "border-slate-900 bg-slate-900 text-white"
                                                                : "border-slate-300 text-slate-700 hover:bg-slate-50"
                                                        }`}
                                                    >
                                                        {role.name}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    ) : (
                                        <p className="text-sm text-slate-500">
                                            All available roles are already assigned.
                                        </p>
                                    )}
                                    <p className="mt-2 text-xs text-slate-500">
                                        {additionalRoleName
                                            ? `Next role to grant: ${additionalRoleName}.`
                                            : "Choose one additional role to grant if needed. Existing roles remain attached to the user."}
                                    </p>
                                </div>

                                <div className="flex items-center gap-2 text-sm text-slate-700">
                                    <input
                                        id="assign-owner-access"
                                        type="checkbox"
                                        checked={promoteToOwner}
                                        disabled={selectedUser.is_owner}
                                        onChange={(event) =>
                                            setPromoteToOwner(event.target.checked)
                                        }
                                    />
                                    <label
                                        htmlFor="assign-owner-access"
                                        className={selectedUser.is_owner ? "" : "cursor-pointer"}
                                    >
                                        {selectedUser.is_owner
                                            ? "This user already has owner access"
                                            : "Promote to owner"}
                                    </label>
                                </div>

                                {assignmentError ? (
                                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                        {assignmentError}
                                    </div>
                                ) : null}

                                <button
                                    type="submit"
                                    disabled={isSavingAccess}
                                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {isSavingAccess ? "Saving..." : "Apply access changes"}
                                </button>
                            </form>
                        ) : (
                            <p className="mt-4 text-sm text-slate-600">
                                Add a user before managing role assignments.
                            </p>
                        )}
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h2 className="text-lg font-semibold text-slate-900">Add user</h2>
                        <p className="mt-1 text-sm text-slate-600">
                            Create or attach a user to this tenant using the existing tenant administration APIs.
                        </p>

                        <form className="mt-5 space-y-4" onSubmit={handleCreateUser}>
                                <div>
                                    <label
                                        htmlFor="settings-user-email"
                                        className="mb-1 block text-sm font-medium text-slate-700"
                                    >
                                        Email
                                    </label>
                                    <input
                                        id="settings-user-email"
                                        value={createForm.email}
                                        onChange={(event) =>
                                            setCreateForm((current) => ({
                                                ...current,
                                                email: event.target.value,
                                            }))
                                        }
                                        type="email"
                                        placeholder="operator@example.com"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                        required
                                    />
                                </div>

                                <div>
                                    <label
                                        htmlFor="settings-user-full-name"
                                        className="mb-1 block text-sm font-medium text-slate-700"
                                    >
                                        Full name
                                    </label>
                                    <input
                                        id="settings-user-full-name"
                                        value={createForm.full_name ?? ""}
                                        onChange={(event) =>
                                            setCreateForm((current) => ({
                                                ...current,
                                                full_name: event.target.value,
                                            }))
                                        }
                                        placeholder="Full name"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                    />
                                </div>

                                <div>
                                    <label
                                        htmlFor="settings-user-password"
                                        className="mb-1 block text-sm font-medium text-slate-700"
                                    >
                                        Temporary password
                                    </label>
                                    <input
                                        id="settings-user-password"
                                        value={createForm.password ?? ""}
                                        onChange={(event) =>
                                            setCreateForm((current) => ({
                                                ...current,
                                                password: event.target.value,
                                            }))
                                        }
                                        type="password"
                                        placeholder="Optional for existing accounts"
                                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                    />
                                </div>

                                <fieldset>
                                    <legend className="text-sm font-medium text-slate-700">
                                        Initial roles
                                    </legend>
                                    <div className="mt-2 grid gap-2">
                                        {roles.map((role) => {
                                            const checked = createForm.role_names.includes(role.name);
                                            const inputId = `create-role-${role.id}`;

                                            return (
                                                <div
                                                    key={role.id}
                                                    className="flex items-start gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700"
                                                >
                                                    <input
                                                        id={inputId}
                                                        type="checkbox"
                                                        checked={checked}
                                                        onChange={(event) =>
                                                            toggleCreateRole(
                                                                role.name,
                                                                event.target.checked,
                                                            )
                                                        }
                                                        className="mt-0.5"
                                                    />
                                                    <label htmlFor={inputId} className="flex-1 cursor-pointer">
                                                        <span className="font-medium text-slate-900">
                                                            {role.name}
                                                        </span>
                                                        <span className="mt-1 block text-xs text-slate-500">
                                                            {role.permission_codes.length > 0
                                                                ? role.permission_codes.join(", ")
                                                                : "No permissions listed"}
                                                        </span>
                                                    </label>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </fieldset>

                                <div className="flex items-center gap-2 text-sm text-slate-700">
                                    <input
                                        id="create-owner-access"
                                        type="checkbox"
                                        checked={createForm.is_owner}
                                        onChange={(event) =>
                                            setCreateForm((current) => ({
                                                ...current,
                                                is_owner: event.target.checked,
                                            }))
                                        }
                                    />
                                    <label htmlFor="create-owner-access" className="cursor-pointer">
                                        Grant owner access
                                    </label>
                                </div>

                                {createError ? (
                                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                        {createError}
                                    </div>
                                ) : null}

                                <button
                                    type="submit"
                                    disabled={isCreatingUser}
                                    className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {isCreatingUser ? "Creating..." : "Add user"}
                                </button>
                        </form>
                    </section>
                </div>
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

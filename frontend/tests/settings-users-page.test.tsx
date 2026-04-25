import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
    within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    pathname: "/settings/users",
    getTenantUsers: vi.fn(),
    getTenantRoles: vi.fn(),
    createTenantUser: vi.fn(),
    assignTenantUserRoles: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    usePathname: () => mocks.pathname,
}));

vi.mock("@/services/tenants.service", () => ({
    getTenantUsers: mocks.getTenantUsers,
    getTenantRoles: mocks.getTenantRoles,
    createTenantUser: mocks.createTenantUser,
    assignTenantUserRoles: mocks.assignTenantUserRoles,
}));

import UsersSettingsRoute from "@/app/(dashboard)/settings/users/page";

const tenantRoles = [
    {
        id: "role-owner",
        name: "owner",
        permission_codes: ["tenant.admin"],
        created_at: "2026-04-08T10:00:00.000Z",
    },
    {
        id: "role-admin",
        name: "admin",
        permission_codes: ["tenant.admin", "billing.access"],
        created_at: "2026-04-08T10:00:00.000Z",
    },
    {
        id: "role-manager",
        name: "manager",
        permission_codes: ["crm.write"],
        created_at: "2026-04-08T10:00:00.000Z",
    },
    {
        id: "role-user",
        name: "user",
        permission_codes: ["crm.read"],
        created_at: "2026-04-08T10:00:00.000Z",
    },
];

const tenantUsers = [
    {
        user_id: "user-1",
        email: "alex@example.com",
        full_name: "Alex Admin",
        user_is_active: true,
        membership_is_active: true,
        is_owner: false,
        role_names: ["admin"],
        membership_created_at: "2026-04-01T10:00:00.000Z",
    },
    {
        user_id: "user-2",
        email: "owner@example.com",
        full_name: null,
        user_is_active: false,
        membership_is_active: true,
        is_owner: true,
        role_names: ["owner", "admin"],
        membership_created_at: "2026-04-02T10:00:00.000Z",
    },
];

function createDeferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;

    const promise = new Promise<T>((nextResolve, nextReject) => {
        resolve = nextResolve;
        reject = nextReject;
    });

    return { promise, resolve, reject };
}

describe("settings users page", () => {
    beforeEach(() => {
        mocks.pathname = "/settings/users";
        mocks.getTenantUsers.mockReset();
        mocks.getTenantRoles.mockReset();
        mocks.createTenantUser.mockReset();
        mocks.assignTenantUserRoles.mockReset();

        mocks.getTenantUsers.mockResolvedValue(tenantUsers);
        mocks.getTenantRoles.mockResolvedValue(tenantRoles);
        mocks.createTenantUser.mockResolvedValue({
            tenant_id: "tenant-1",
            user_id: "user-3",
            email: "new.user@example.com",
            created_user: true,
            created_credentials: true,
            password_set: true,
            created_membership: true,
            is_owner: false,
            assigned_roles: ["user", "manager"],
            created_role_assignments: ["user", "manager"],
        });
        mocks.assignTenantUserRoles.mockResolvedValue({
            tenant_id: "tenant-1",
            user_id: "user-1",
            is_owner: true,
            assigned_roles: ["admin", "manager", "owner"],
            created_role_assignments: ["manager", "owner"],
        });
    });

    afterEach(() => {
        cleanup();
    });

    function getUsersTableSection(): HTMLElement {
        const section = screen
            .getByRole("heading", { name: "Tenant users" })
            .closest("section");
        expect(section).toBeTruthy();
        return section as HTMLElement;
    }

    function getManageRolesSection(): HTMLElement {
        const section = screen
            .getByRole("heading", { name: "Manage roles" })
            .closest("section");
        expect(section).toBeTruthy();
        return section as HTMLElement;
    }

    it("loads tenant users and renders the operational users table", async () => {
        render(<UsersSettingsRoute />);

        await waitFor(() => {
            expect(mocks.getTenantUsers).toHaveBeenCalledTimes(1);
            expect(mocks.getTenantRoles).toHaveBeenCalledTimes(1);
        });

        expect(screen.getByRole("heading", { name: "Users & Roles", level: 1 })).toBeTruthy();
        const usersTableSection = within(getUsersTableSection());
        const manageRolesSection = within(getManageRolesSection());

        expect(usersTableSection.getByText("Alex Admin")).toBeTruthy();
        expect(usersTableSection.getByText("owner@example.com")).toBeTruthy();
        expect(usersTableSection.getByText("User disabled")).toBeTruthy();
        expect(screen.getAllByText("Owner").length).toBeGreaterThan(0);
        expect(screen.getAllByText("admin").length).toBeGreaterThan(0);
        expect(
            manageRolesSection.getByRole("button", { name: "manager" }),
        ).toBeTruthy();
    });

    it("shows a loading state before the users request resolves", async () => {
        const usersDeferred = createDeferred<typeof tenantUsers>();
        const rolesDeferred = createDeferred<typeof tenantRoles>();
        mocks.getTenantUsers.mockReturnValueOnce(usersDeferred.promise);
        mocks.getTenantRoles.mockReturnValueOnce(rolesDeferred.promise);

        render(<UsersSettingsRoute />);

        expect(screen.getByText(/Loading tenant users/i)).toBeTruthy();

        usersDeferred.resolve(tenantUsers);
        rolesDeferred.resolve(tenantRoles);

        await waitFor(() => {
            expect(within(getUsersTableSection()).getByText("Alex Admin")).toBeTruthy();
        });
    });

    it("shows an empty state when no tenant users exist", async () => {
        mocks.getTenantUsers.mockResolvedValueOnce([]);

        render(<UsersSettingsRoute />);

        await waitFor(() => {
            expect(
                screen.getByText(/No tenant users exist yet/i),
            ).toBeTruthy();
        });
        expect(
            screen.getByText(/Add a user before managing role assignments/i),
        ).toBeTruthy();
    });

    it("shows an error state when the tenant users request fails", async () => {
        mocks.getTenantUsers.mockRejectedValueOnce(
            new Error("tenant users unavailable"),
        );

        render(<UsersSettingsRoute />);

        await waitFor(() => {
            expect(
                screen.getByRole("heading", { name: /Unable to load users/i }),
            ).toBeTruthy();
        });
        expect(screen.getByText("tenant users unavailable")).toBeTruthy();
        expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
    });

    it("submits the add user flow through the existing tenant user service", async () => {
        mocks.getTenantUsers
            .mockResolvedValueOnce(tenantUsers)
            .mockResolvedValueOnce([
                ...tenantUsers,
                {
                    user_id: "user-3",
                    email: "new.user@example.com",
                    full_name: "New User",
                    user_is_active: true,
                    membership_is_active: true,
                    is_owner: false,
                    role_names: ["manager", "user"],
                    membership_created_at: "2026-04-03T10:00:00.000Z",
                },
            ]);

        render(<UsersSettingsRoute />);

        await waitFor(() => {
            expect(within(getUsersTableSection()).getByText("Alex Admin")).toBeTruthy();
        });

        const addUserSection = screen
            .getByRole("heading", { name: "Add user" })
            .closest("section");
        expect(addUserSection).toBeTruthy();

        const scoped = within(addUserSection as HTMLElement);
        fireEvent.change(scoped.getByLabelText("Email"), {
            target: { value: "  new.user@example.com  " },
        });
        fireEvent.change(scoped.getByLabelText("Full name"), {
            target: { value: "  New User  " },
        });
        fireEvent.change(scoped.getByLabelText("Temporary password"), {
            target: { value: "  TempPass123!  " },
        });
        fireEvent.click(
            scoped.getByRole("checkbox", {
                name: /manager/i,
            }),
        );
        fireEvent.click(scoped.getByRole("button", { name: "Add user" }));

        await waitFor(() => {
            expect(mocks.createTenantUser).toHaveBeenCalledTimes(1);
        });
        expect(mocks.createTenantUser).toHaveBeenCalledWith({
            email: "new.user@example.com",
            full_name: "New User",
            password: "TempPass123!",
            role_names: ["manager", "user"],
            is_owner: false,
        });

        await waitFor(() => {
            expect(
                screen.getByText("User new.user@example.com added successfully."),
            ).toBeTruthy();
        });
    });

    it("submits the role assignment flow through the existing tenant role service", async () => {
        mocks.getTenantUsers
            .mockResolvedValueOnce(tenantUsers)
            .mockResolvedValueOnce([
                {
                    ...tenantUsers[0],
                    is_owner: true,
                    role_names: ["admin", "manager"],
                },
                tenantUsers[1],
            ]);

        render(<UsersSettingsRoute />);

        await waitFor(() => {
            expect(within(getUsersTableSection()).getByText("Alex Admin")).toBeTruthy();
        });

        const scoped = within(getManageRolesSection());
        fireEvent.click(scoped.getByLabelText(/Promote to owner/i));
        fireEvent.click(
            scoped.getByRole("button", { name: "Apply access changes" }),
        );

        await waitFor(() => {
            expect(mocks.assignTenantUserRoles).toHaveBeenCalledTimes(1);
        });
        expect(mocks.assignTenantUserRoles).toHaveBeenCalledWith("user-1", {
            role_names: ["admin"],
            is_owner: true,
        });

        await waitFor(() => {
            expect(
                screen.getByText("Access updated for alex@example.com."),
            ).toBeTruthy();
        });
    });
});

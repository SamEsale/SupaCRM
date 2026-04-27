import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    pathname: "/settings/security",
    authState: {
        user: {
            user_id: "user-1",
            tenant_id: "tenant-1",
            email: "alex@example.com",
            full_name: "Alex Admin",
            roles: ["admin"],
            is_owner: false,
            user_is_active: true,
            membership_is_active: true,
            tenant_is_active: true,
        },
        accessToken: "access-token",
        refreshToken: "refresh-token",
        isAuthenticated: true,
        isReady: true,
    },
    getCurrentTenant: vi.fn(),
    getCurrentUser: vi.fn(),
    getTenantRoles: vi.fn(),
    getTenantUsers: vi.fn(),
    requestPasswordReset: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    usePathname: () => mocks.pathname,
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => mocks.authState,
}));

vi.mock("@/services/tenants.service", () => ({
    getCurrentTenant: mocks.getCurrentTenant,
    getTenantRoles: mocks.getTenantRoles,
    getTenantUsers: mocks.getTenantUsers,
}));

vi.mock("@/services/auth.service", () => ({
    getCurrentUser: mocks.getCurrentUser,
    requestPasswordReset: mocks.requestPasswordReset,
}));

vi.mock("@/components/auth/logout-button", () => ({
    default: () => <button type="button">Sign out</button>,
}));

import SecuritySettingsRoute from "@/app/(dashboard)/settings/security/page";

const tenant = {
    id: "tenant-1",
    name: "Northwind Labs",
    is_active: true,
    status: "active" as const,
    status_reason: null,
    created_at: "2026-04-01T10:00:00.000Z",
    updated_at: "2026-04-08T10:00:00.000Z",
};

const currentUser = {
    user_id: "user-1",
    tenant_id: "tenant-1",
    email: "alex@example.com",
    full_name: "Alex Admin",
    roles: ["admin"],
    is_owner: false,
    user_is_active: true,
    membership_is_active: true,
    tenant_is_active: true,
};

const tenantRoles = [
    {
        id: "role-owner",
        name: "owner",
        permission_codes: ["billing.access", "tenant.admin"],
        created_at: "2026-04-01T10:00:00.000Z",
    },
    {
        id: "role-admin",
        name: "admin",
        permission_codes: ["billing.access", "tenant.admin"],
        created_at: "2026-04-01T10:00:00.000Z",
    },
    {
        id: "role-manager",
        name: "manager",
        permission_codes: ["crm.write", "reporting.read"],
        created_at: "2026-04-01T10:00:00.000Z",
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
        full_name: "Olivia Owner",
        user_is_active: true,
        membership_is_active: true,
        is_owner: true,
        role_names: ["owner", "admin"],
        membership_created_at: "2026-04-01T10:00:00.000Z",
    },
    {
        user_id: "user-3",
        email: "inactive@example.com",
        full_name: null,
        user_is_active: true,
        membership_is_active: false,
        is_owner: false,
        role_names: ["user"],
        membership_created_at: "2026-04-01T10:00:00.000Z",
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

describe("settings security page", () => {
    beforeEach(() => {
        mocks.pathname = "/settings/security";
        mocks.authState = {
            user: {
                ...currentUser,
            },
            accessToken: "access-token",
            refreshToken: "refresh-token",
            isAuthenticated: true,
            isReady: true,
        };
        mocks.getCurrentTenant.mockReset();
        mocks.getCurrentUser.mockReset();
        mocks.getTenantRoles.mockReset();
        mocks.getTenantUsers.mockReset();
        mocks.requestPasswordReset.mockReset();

        mocks.getCurrentTenant.mockResolvedValue(tenant);
        mocks.getCurrentUser.mockResolvedValue(currentUser);
        mocks.getTenantRoles.mockResolvedValue(tenantRoles);
        mocks.getTenantUsers.mockResolvedValue(tenantUsers);
        mocks.requestPasswordReset.mockResolvedValue({
            message: "If the account exists, password reset instructions have been created.",
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("loads the real security sections for the current tenant", async () => {
        render(<SecuritySettingsRoute />);

        await waitFor(() => {
            expect(mocks.getCurrentTenant).toHaveBeenCalledTimes(1);
            expect(mocks.getCurrentUser).toHaveBeenCalledWith("tenant-1");
            expect(mocks.getTenantRoles).toHaveBeenCalledTimes(1);
            expect(mocks.getTenantUsers).toHaveBeenCalledTimes(1);
        });

        expect(screen.getByRole("heading", { name: "Security", level: 1 })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Account security" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Access & permissions" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Session / auth state" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Password / recovery" })).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Tenant security posture" })).toBeTruthy();
    });

    it("renders the current account and tenant summary from live auth and tenant data", async () => {
        render(<SecuritySettingsRoute />);

        await waitFor(() => {
            expect(screen.getByText("Northwind Labs")).toBeTruthy();
        });

        expect(screen.getByText("Alex Admin")).toBeTruthy();
        expect(screen.getAllByText("alex@example.com").length).toBeGreaterThan(0);
        expect(screen.getByText("tenant-1")).toBeTruthy();
        expect(screen.getByText("Active membership")).toBeTruthy();
        expect(screen.getByText("Tenant active")).toBeTruthy();
    });

    it("renders grounded role and permission visibility", async () => {
        render(<SecuritySettingsRoute />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Tenant role catalog" })).toBeTruthy();
        });

        expect(screen.getAllByText("admin").length).toBeGreaterThan(0);
        expect(screen.getAllByText("tenant.admin").length).toBeGreaterThan(0);
        expect(screen.getByText("Manage tenant administration settings")).toBeTruthy();
        expect(screen.getByText("Operational administrator for tenant settings, billing, and day-to-day oversight.")).toBeTruthy();
    });

    it("renders only supported security actions and omits unsupported ones", async () => {
        render(<SecuritySettingsRoute />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: "Request reset instructions" })).toBeTruthy();
        });

        expect(screen.getByRole("button", { name: "Sign out" })).toBeTruthy();
        expect(screen.queryByRole("button", { name: /log out all sessions/i })).toBeNull();
        expect(screen.queryByRole("button", { name: /change password/i })).toBeNull();
    });

    it("submits the supported password reset request flow", async () => {
        render(<SecuritySettingsRoute />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: "Request reset instructions" })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: "Request reset instructions" }));

        await waitFor(() => {
            expect(mocks.requestPasswordReset).toHaveBeenCalledWith({
                tenant_id: "tenant-1",
                email: "alex@example.com",
            });
        });
        expect(
            screen.getByText("If the account exists, password reset instructions have been created."),
        ).toBeTruthy();
    });

    it("shows a loading state before the security queries resolve", async () => {
        const tenantDeferred = createDeferred<typeof tenant>();
        const userDeferred = createDeferred<typeof currentUser>();
        const rolesDeferred = createDeferred<typeof tenantRoles>();
        const usersDeferred = createDeferred<typeof tenantUsers>();

        mocks.getCurrentTenant.mockReturnValueOnce(tenantDeferred.promise);
        mocks.getCurrentUser.mockReturnValueOnce(userDeferred.promise);
        mocks.getTenantRoles.mockReturnValueOnce(rolesDeferred.promise);
        mocks.getTenantUsers.mockReturnValueOnce(usersDeferred.promise);

        render(<SecuritySettingsRoute />);

        expect(screen.getByText(/Loading security settings/i)).toBeTruthy();

        tenantDeferred.resolve(tenant);
        userDeferred.resolve(currentUser);
        rolesDeferred.resolve(tenantRoles);
        usersDeferred.resolve(tenantUsers);

        await waitFor(() => {
            expect(screen.getByText("Northwind Labs")).toBeTruthy();
        });
    });

    it("shows an error state when the security queries fail", async () => {
        mocks.getCurrentTenant.mockRejectedValueOnce(new Error("security endpoint unavailable"));

        render(<SecuritySettingsRoute />);

        await waitFor(() => {
            expect(
                screen.getByRole("heading", { name: /Unable to load security settings/i }),
            ).toBeTruthy();
        });
        expect(screen.getByText("security endpoint unavailable")).toBeTruthy();
        expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
    });
});

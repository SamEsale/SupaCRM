import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    pathname: "/settings/users",
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
    getTenantUsers: vi.fn(),
    getTenantRoles: vi.fn(),
    updateTenantMembership: vi.fn(),
    removeTenantMembership: vi.fn(),
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
    getTenantUsers: mocks.getTenantUsers,
    getTenantRoles: mocks.getTenantRoles,
    updateTenantMembership: mocks.updateTenantMembership,
    removeTenantMembership: mocks.removeTenantMembership,
}));

vi.mock("@/services/auth.service", () => ({
    getCurrentUser: mocks.getCurrentUser,
    requestPasswordReset: mocks.requestPasswordReset,
}));

vi.mock("@/components/auth/logout-button", () => ({
    default: () => <button type="button">Sign out</button>,
}));

import Sidebar from "@/components/navigation/Sidebar";
import MembershipSettingsPage from "@/app/(dashboard)/settings/membership/page";
import SecuritySettingsPage from "@/app/(dashboard)/settings/security/page";

describe("settings navigation", () => {
    beforeEach(() => {
        mocks.pathname = "/settings/users";
        mocks.getCurrentTenant.mockReset();
        mocks.getCurrentUser.mockReset();
        mocks.getTenantUsers.mockReset();
        mocks.getTenantRoles.mockReset();
        mocks.updateTenantMembership.mockReset();
        mocks.removeTenantMembership.mockReset();
        mocks.requestPasswordReset.mockReset();
        mocks.getCurrentTenant.mockResolvedValue({
            id: "tenant-1",
            name: "Northwind Labs",
            is_active: true,
            status: "active",
            status_reason: null,
            created_at: "2026-04-01T10:00:00.000Z",
            updated_at: "2026-04-08T10:00:00.000Z",
        });
        mocks.getCurrentUser.mockResolvedValue({
            user_id: "user-1",
            tenant_id: "tenant-1",
            email: "alex@example.com",
            full_name: "Alex Admin",
            roles: ["admin"],
            is_owner: false,
            user_is_active: true,
            membership_is_active: true,
            tenant_is_active: true,
        });
        mocks.getTenantUsers.mockResolvedValue([]);
        mocks.getTenantRoles.mockResolvedValue([
            {
                id: "role-admin",
                name: "admin",
                permission_codes: ["tenant.admin"],
                created_at: "2026-04-08T10:00:00.000Z",
            },
        ]);
        mocks.requestPasswordReset.mockResolvedValue({
            message: "If the account exists, password reset instructions have been created.",
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders the expanded settings entries inside the real sidebar navigation", () => {
        render(<Sidebar branding={null} />);

        fireEvent.click(screen.getByRole("button", { name: "Settings" }));

        expect(screen.getByRole("link", { name: "Branding" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Company" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Integrations" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Users & Roles" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Membership" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Security" })).toBeTruthy();
    });

    it("renders the membership route scaffold inside the settings information architecture", () => {
        mocks.pathname = "/settings/membership";

        render(<MembershipSettingsPage />);

        expect(
            screen.getByRole("heading", { name: "Membership", level: 1 }),
        ).toBeTruthy();
        expect(
            screen.getByText(/Manage tenant access state, ownership lifecycle/i),
        ).toBeTruthy();
        expect(screen.getByRole("link", { name: "Company" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Branding" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Integrations" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Users & Roles" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Security" })).toBeTruthy();
    });

    it("renders the security route inside the settings information architecture", async () => {
        mocks.pathname = "/settings/security";

        render(<SecuritySettingsPage />);

        await screen.findByRole("heading", { name: "Security", level: 1 });
        expect(screen.getByRole("heading", { name: "Account security" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Company" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Branding" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Integrations" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Users & Roles" })).toBeTruthy();
        expect(screen.getByRole("link", { name: "Membership" })).toBeTruthy();
    });
});

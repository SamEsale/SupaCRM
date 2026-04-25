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
    pathname: "/settings/membership",
    getTenantUsers: vi.fn(),
    updateTenantMembership: vi.fn(),
    removeTenantMembership: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    usePathname: () => mocks.pathname,
}));

vi.mock("@/services/tenants.service", () => ({
    getTenantUsers: mocks.getTenantUsers,
    updateTenantMembership: mocks.updateTenantMembership,
    removeTenantMembership: mocks.removeTenantMembership,
}));

import MembershipSettingsRoute from "@/app/(dashboard)/settings/membership/page";

const tenantMembers = [
    {
        user_id: "owner-1",
        email: "owner@example.com",
        full_name: "Olivia Owner",
        user_is_active: true,
        membership_is_active: true,
        is_owner: true,
        role_names: ["owner", "admin"],
        membership_created_at: "2026-04-01T10:00:00.000Z",
    },
    {
        user_id: "admin-2",
        email: "admin@example.com",
        full_name: "Alex Admin",
        user_is_active: true,
        membership_is_active: true,
        is_owner: false,
        role_names: ["admin"],
        membership_created_at: "2026-04-02T10:00:00.000Z",
    },
    {
        user_id: "user-3",
        email: "inactive@example.com",
        full_name: null,
        user_is_active: true,
        membership_is_active: false,
        is_owner: false,
        role_names: ["user"],
        membership_created_at: "2026-04-03T10:00:00.000Z",
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

describe("settings membership page", () => {
    beforeEach(() => {
        mocks.pathname = "/settings/membership";
        mocks.getTenantUsers.mockReset();
        mocks.updateTenantMembership.mockReset();
        mocks.removeTenantMembership.mockReset();

        mocks.getTenantUsers.mockResolvedValue(tenantMembers);
        mocks.updateTenantMembership.mockResolvedValue({
            tenant_id: "tenant-1",
            user_id: "admin-2",
            membership_is_active: false,
            is_owner: false,
            transferred_owner_from_user_id: null,
        });
        mocks.removeTenantMembership.mockResolvedValue({
            tenant_id: "tenant-1",
            user_id: "user-3",
            removed: true,
        });

        vi.spyOn(window, "confirm").mockReturnValue(true);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        cleanup();
    });

    function getMembershipSection(): HTMLElement {
        const section = screen
            .getByRole("heading", { name: "Tenant membership" })
            .closest("section");
        expect(section).toBeTruthy();
        return section as HTMLElement;
    }

    it("loads tenant members and renders the membership lifecycle table", async () => {
        render(<MembershipSettingsRoute />);

        await waitFor(() => {
            expect(mocks.getTenantUsers).toHaveBeenCalledTimes(1);
        });

        expect(
            screen.getByRole("heading", { name: "Membership", level: 1 }),
        ).toBeTruthy();
        const membershipSection = within(getMembershipSection());
        expect(membershipSection.getByText("Olivia Owner")).toBeTruthy();
        expect(membershipSection.getByText("Alex Admin")).toBeTruthy();
        expect(membershipSection.getAllByText("inactive@example.com").length).toBeGreaterThan(0);
        expect(membershipSection.getByText("Membership inactive")).toBeTruthy();
        expect(screen.getByRole("button", { name: "Transfer ownership" })).toBeTruthy();
    });

    it("shows a loading state before membership data resolves", async () => {
        const membersDeferred = createDeferred<typeof tenantMembers>();
        mocks.getTenantUsers.mockReturnValueOnce(membersDeferred.promise);

        render(<MembershipSettingsRoute />);

        expect(screen.getByText(/Loading tenant membership/i)).toBeTruthy();

        membersDeferred.resolve(tenantMembers);

        await waitFor(() => {
            expect(within(getMembershipSection()).getByText("Olivia Owner")).toBeTruthy();
        });
    });

    it("shows an empty state when no tenant members exist", async () => {
        mocks.getTenantUsers.mockResolvedValueOnce([]);

        render(<MembershipSettingsRoute />);

        await waitFor(() => {
            expect(
                screen.getByText(/No tenant members were found/i),
            ).toBeTruthy();
        });
    });

    it("calls the membership service when deactivating a member", async () => {
        mocks.getTenantUsers
            .mockResolvedValueOnce(tenantMembers)
            .mockResolvedValueOnce([
                tenantMembers[0],
                { ...tenantMembers[1], membership_is_active: false },
                tenantMembers[2],
            ]);

        render(<MembershipSettingsRoute />);

        await waitFor(() => {
            expect(within(getMembershipSection()).getByText("Alex Admin")).toBeTruthy();
        });

        const deactivateButtons = within(getMembershipSection()).getAllByRole("button", {
            name: "Deactivate",
        });
        fireEvent.click(deactivateButtons[1]);

        await waitFor(() => {
            expect(mocks.updateTenantMembership).toHaveBeenCalledWith("admin-2", {
                membership_is_active: false,
            });
        });
        expect(window.confirm).toHaveBeenCalled();
        await waitFor(() => {
            expect(
                screen.getByText("Membership deactivated for admin@example.com."),
            ).toBeTruthy();
        });
    });

    it("calls the membership service when reactivating a member", async () => {
        mocks.getTenantUsers
            .mockResolvedValueOnce(tenantMembers)
            .mockResolvedValueOnce([
                tenantMembers[0],
                tenantMembers[1],
                { ...tenantMembers[2], membership_is_active: true },
            ]);

        render(<MembershipSettingsRoute />);

        await waitFor(() => {
            expect(
                within(getMembershipSection()).getAllByText("inactive@example.com").length,
            ).toBeGreaterThan(0);
        });

        fireEvent.click(screen.getByRole("button", { name: "Reactivate" }));

        await waitFor(() => {
            expect(mocks.updateTenantMembership).toHaveBeenCalledWith("user-3", {
                membership_is_active: true,
            });
        });
        await waitFor(() => {
            expect(
                screen.getByText("Membership reactivated for inactive@example.com."),
            ).toBeTruthy();
        });
    });

    it("calls the membership service when removing a member", async () => {
        mocks.getTenantUsers
            .mockResolvedValueOnce(tenantMembers)
            .mockResolvedValueOnce([tenantMembers[0], tenantMembers[1]]);

        render(<MembershipSettingsRoute />);

        await waitFor(() => {
            expect(
                within(getMembershipSection()).getAllByText("inactive@example.com").length,
            ).toBeGreaterThan(0);
        });

        const removeButtons = within(getMembershipSection()).getAllByRole("button", {
            name: "Remove",
        });
        fireEvent.click(removeButtons[2]);

        await waitFor(() => {
            expect(mocks.removeTenantMembership).toHaveBeenCalledWith("user-3");
        });
        await waitFor(() => {
            expect(
                screen.getByText("Membership removed for inactive@example.com."),
            ).toBeTruthy();
        });
    });

    it("renders conflict errors returned by the membership lifecycle backend", async () => {
        mocks.updateTenantMembership.mockRejectedValueOnce({
            response: {
                data: {
                    detail: "Cannot deactivate the last active owner for tenant tenant-1.",
                },
            },
        });

        render(<MembershipSettingsRoute />);

        await waitFor(() => {
            expect(within(getMembershipSection()).getByText("Olivia Owner")).toBeTruthy();
        });

        const deactivateButtons = within(getMembershipSection()).getAllByRole("button", {
            name: "Deactivate",
        });
        fireEvent.click(deactivateButtons[0]);

        await waitFor(() => {
            expect(
                screen.getByText("Cannot deactivate the last active owner for tenant tenant-1."),
            ).toBeTruthy();
        });
    });
});

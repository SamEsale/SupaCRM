import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: pushMock,
        refresh: refreshMock,
    }),
}));

vi.mock("@/services/auth.service", () => ({
    login: vi.fn(),
    getCurrentUser: vi.fn(),
}));

vi.mock("@/lib/auth-storage", () => ({
    setAuthStorage: vi.fn(),
    setTenantId: vi.fn(),
    setTokenStorage: vi.fn(),
}));

import LoginForm from "@/components/auth/login-form";
import { getCurrentUser, login } from "@/services/auth.service";
import { setTenantId } from "@/lib/auth-storage";

describe("LoginForm", () => {
    beforeEach(() => {
        pushMock.mockReset();
        refreshMock.mockReset();

        vi.mocked(login).mockResolvedValue({
            access_token: "access-token",
            refresh_token: "refresh-token",
            tenant_id: "tenant-1",
            token_type: "bearer",
            access_token_expires_at: new Date().toISOString(),
            refresh_token_expires_at: new Date().toISOString(),
        });

        vi.mocked(getCurrentUser).mockResolvedValue({
            user_id: "user-1",
            tenant_id: "tenant-1",
            email: "owner@example.com",
            full_name: "Owner User",
            roles: ["owner"],
            is_owner: true,
            user_is_active: true,
            membership_is_active: true,
            tenant_is_active: true,
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("submits only email and password and stores tenant id from the token response", async () => {
        render(<LoginForm />);

        fireEvent.change(screen.getByLabelText(/email/i), {
            target: { value: "owner@example.com" },
        });
        fireEvent.change(screen.getByLabelText(/password/i), {
            target: { value: "Password1234!" },
        });

        fireEvent.submit(screen.getByRole("button", { name: /sign in/i }));

        await waitFor(() => {
            expect(login).toHaveBeenCalledWith({
                email: "owner@example.com",
                password: "Password1234!",
            });
        });

        expect(vi.mocked(login).mock.calls[0]?.[0]).not.toHaveProperty("tenant_id");
        expect(setTenantId).toHaveBeenCalledWith("tenant-1");
        expect(getCurrentUser).toHaveBeenCalledWith("tenant-1");
        expect(pushMock).toHaveBeenCalledWith("/dashboard");
        expect(refreshMock).toHaveBeenCalledTimes(1);
    });
});

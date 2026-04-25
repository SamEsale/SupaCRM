import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import LoginForm from "@/components/auth/login-form";
import { getCurrentUser, login } from "@/services/auth.service";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: pushMock,
        refresh: refreshMock,
    }),
}));

vi.mock("@/components/auth/login-mode", () => ({
    isLocalLoginHost: () => true,
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

describe("LoginForm local mode", () => {
    beforeEach(() => {
        localStorage.clear();
        pushMock.mockReset();
        refreshMock.mockReset();
    });

    afterEach(() => {
        localStorage.clear();
        cleanup();
    });

    it("hides the tenant field and submits email/password only on localhost", async () => {
        vi.mocked(login).mockResolvedValue({
            access_token: "access-token",
            refresh_token: "refresh-token",
            tenant_id: "supacrm-test",
            token_type: "bearer",
            access_token_expires_at: new Date().toISOString(),
            refresh_token_expires_at: new Date().toISOString(),
        });
        vi.mocked(getCurrentUser).mockResolvedValue({
            user_id: "user-1",
            tenant_id: "supacrm-test",
            email: "supacrm@test.com",
            full_name: "SupaCRM",
            roles: ["owner"],
            is_owner: true,
            user_is_active: true,
            membership_is_active: true,
            tenant_is_active: true,
        });

        render(<LoginForm isLocalLogin={true} />);

        await waitFor(() => {
            expect(screen.queryByLabelText(/tenant id/i)).toBeNull();
        });

        fireEvent.change(screen.getByLabelText(/email/i), {
            target: { value: "supacrm@test.com" },
        });
        fireEvent.change(screen.getByLabelText(/password/i), {
            target: { value: "AdminTest123!" },
        });
        fireEvent.submit(screen.getByRole("button", { name: /sign in/i }));

        await waitFor(() => {
            expect(login).toHaveBeenCalledWith({
                email: "supacrm@test.com",
                password: "AdminTest123!",
            });
        });

        expect(getCurrentUser).toHaveBeenCalledWith("supacrm-test");
        expect(pushMock).toHaveBeenCalledWith("/dashboard");
        expect(refreshMock).toHaveBeenCalledTimes(1);
    });

    it("shows the normalized backend error message when login fails", async () => {
        vi.mocked(login).mockRejectedValue({
            response: {
                status: 401,
                data: {
                    error: {
                        code: "unauthorized",
                        message: "Invalid or expired token",
                    },
                },
            },
            message: "Request failed with status code 401",
        });

        render(<LoginForm isLocalLogin={true} />);

        fireEvent.change(screen.getByLabelText(/email/i), {
            target: { value: "supacrm@test.com" },
        });
        fireEvent.change(screen.getByLabelText(/password/i), {
            target: { value: "bad-password" },
        });
        fireEvent.submit(screen.getByRole("button", { name: /sign in/i }));

        await waitFor(() => {
            expect(screen.getByText("Invalid or expired token")).toBeTruthy();
        });
    });
});

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    push: vi.fn(),
    replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: mocks.push,
        replace: mocks.replace,
    }),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

import ProtectedRoute from "@/components/auth/protected-route";

afterEach(() => {
    cleanup();
    mocks.push.mockReset();
    mocks.replace.mockReset();
});

describe("ProtectedRoute hydration", () => {
    it("renders a stable loading shell before showing protected children", async () => {
        render(
            <ProtectedRoute>
                <div>Protected content</div>
            </ProtectedRoute>,
        );

        expect(screen.getByText(/loading session/i)).toBeTruthy();

        await waitFor(() => {
            expect(screen.getByText(/protected content/i)).toBeTruthy();
        });
    });
});

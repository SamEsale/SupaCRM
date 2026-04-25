import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import axios, {
    AxiosError,
    AxiosHeaders,
    type AxiosResponse,
} from "axios";
import { act, renderHook, waitFor } from "@testing-library/react";

import { authNavigation, apiClient } from "@/lib/api-client";
import {
    clearAuthStorage,
    getAuthStateFromStorage,
    setAuthStorage,
    updateAuthTokens,
} from "@/lib/auth-storage";
import { useAuth } from "@/hooks/use-auth";
import type { AuthUser, TokenResponse } from "@/types/auth";
import {
    ACCESS_TOKEN_KEY,
    AUTH_USER_KEY,
    REFRESH_TOKEN_KEY,
    TENANT_ID_KEY,
} from "@/constants/auth";

function buildResponse<T>(
    config: unknown,
    status: number,
    data: T,
): AxiosResponse<T> {
    return {
        data,
        status,
        statusText: status === 200 ? "OK" : "Unauthorized",
        headers: {},
        config: config as never,
        request: {},
    };
}

function buildUnauthorizedError(config: unknown): AxiosError {
    const response = buildResponse(config, 401, { detail: "expired" });

    return new AxiosError(
        "Request failed with status code 401",
        "ERR_BAD_REQUEST",
        config as never,
        {},
        response,
    );
}

function headerValue(headers: unknown, key: string): string | null {
    const normalized = AxiosHeaders.from(headers as never);
    const value = normalized.get(key);
    if (Array.isArray(value)) {
        return value.length > 0 ? String(value[0]) : null;
    }
    return value ? String(value) : null;
}

const originalAdapter = apiClient.defaults.adapter;

const baseUser: AuthUser = {
    user_id: "user-123",
    tenant_id: "tenant-123",
    email: "owner@example.com",
    full_name: "Owner User",
    roles: ["tenant.admin"],
    is_owner: true,
    user_is_active: true,
    membership_is_active: true,
    tenant_is_active: true,
};

beforeEach(() => {
    localStorage.clear();
    apiClient.defaults.adapter = originalAdapter;
});

afterEach(() => {
    localStorage.clear();
    apiClient.defaults.adapter = originalAdapter;
});

describe("frontend auth propagation", () => {
    it("refreshes once, retries the protected request, and stores rotated tokens", async () => {
        setAuthStorage("access-old", "refresh-old", baseUser);

        const requestHeaders: Array<string | null> = [];
        apiClient.defaults.adapter = vi.fn(async (config) => {
            requestHeaders.push(headerValue(config.headers, "Authorization"));

            if (requestHeaders.length === 1) {
                throw buildUnauthorizedError(config);
            }

            return buildResponse(config, 200, { ok: true });
        });

        const refreshResponse: TokenResponse = {
            access_token: "access-new",
            refresh_token: "refresh-new",
            tenant_id: "tenant-123",
            token_type: "bearer",
            access_token_expires_at: new Date(Date.now() + 60_000).toISOString(),
            refresh_token_expires_at: new Date(Date.now() + 600_000).toISOString(),
        };

        const refreshSpy = vi.spyOn(axios, "post").mockResolvedValue(
            buildResponse({}, 200, refreshResponse),
        );

        const response = await apiClient.get<{ ok: boolean }>("/crm/companies");

        expect(response.data).toEqual({ ok: true });
        expect(refreshSpy).toHaveBeenCalledTimes(1);
        expect(requestHeaders).toEqual(["Bearer access-old", "Bearer access-new"]);
        expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe("access-new");
        expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe("refresh-new");
        expect(getAuthStateFromStorage().isAuthenticated).toBe(true);
    });

    it("clears auth state and redirects when refresh fails", async () => {
        setAuthStorage("access-old", "refresh-old", baseUser);

        apiClient.defaults.adapter = vi.fn(async (config) =>
            Promise.reject(buildUnauthorizedError(config)),
        );

        const refreshSpy = vi.spyOn(axios, "post").mockRejectedValue(
            new Error("refresh failed"),
        );
        const redirectSpy = vi
            .spyOn(authNavigation, "redirectToLogin")
            .mockImplementation(() => undefined);

        await expect(apiClient.get("/crm/companies")).rejects.toBeTruthy();

        expect(refreshSpy).toHaveBeenCalledTimes(1);
        expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
        expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
        expect(localStorage.getItem(AUTH_USER_KEY)).toBeNull();
        expect(localStorage.getItem(TENANT_ID_KEY)).toBeNull();
        expect(getAuthStateFromStorage().isAuthenticated).toBe(false);
        expect(redirectSpy).toHaveBeenCalledTimes(1);
    });

    it("keeps useAuth synchronized with token updates and clear events", async () => {
        const { result } = renderHook(() => useAuth());

        expect(result.current.isAuthenticated).toBe(false);

        act(() => {
            setAuthStorage("access-1", "refresh-1", baseUser);
        });

        await waitFor(() => {
            expect(result.current.isAuthenticated).toBe(true);
            expect(result.current.accessToken).toBe("access-1");
            expect(result.current.refreshToken).toBe("refresh-1");
            expect(result.current.user).toEqual(baseUser);
        });

        act(() => {
            updateAuthTokens("access-2", "refresh-2");
        });

        await waitFor(() => {
            expect(result.current.accessToken).toBe("access-2");
            expect(result.current.refreshToken).toBe("refresh-2");
            expect(result.current.user).toEqual(baseUser);
        });

        act(() => {
            clearAuthStorage();
        });

        await waitFor(() => {
            expect(result.current.isAuthenticated).toBe(false);
            expect(result.current.accessToken).toBeNull();
            expect(result.current.refreshToken).toBeNull();
            expect(result.current.user).toBeNull();
        });
    });

    it("uses the stored auth user as the canonical tenant source even if the raw tenant key is stale", async () => {
        setAuthStorage("access-1", "refresh-1", baseUser);
        localStorage.setItem(TENANT_ID_KEY, "tenant-stale");

        apiClient.defaults.adapter = vi.fn(async (config) => {
            expect(headerValue(config.headers, "X-Tenant-Id")).toBe(
                baseUser.tenant_id,
            );
            return buildResponse(config, 200, { ok: true });
        });

        await expect(apiClient.get<{ ok: boolean }>("/crm/companies")).resolves.toEqual(
            expect.objectContaining({
                data: { ok: true },
            }),
        );
    });
});

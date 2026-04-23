import axios, {
    AxiosError,
    AxiosHeaders,
    type AxiosRequestConfig,
} from "axios";

import { API_BASE_URL } from "@/constants/env";
import { applyNormalizedApiErrorMessage } from "@/lib/api-errors";
import {
    clearAuthStorage,
    getAccessToken,
    getRefreshToken,
    getTenantId,
    updateAuthTokens,
} from "@/lib/auth-storage";
import type { TokenResponse } from "@/types/auth";

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

function normalizePath(url: string): string {
    const withoutOrigin = url.replace(/^https?:\/\/[^/]+/i, "");
    if (withoutOrigin.startsWith("/")) {
        return withoutOrigin;
    }
    return `/${withoutOrigin}`;
}

function isPublicPath(path: string): boolean {
    return (
        path.startsWith("/auth/login") ||
        path.startsWith("/auth/register") ||
        path.startsWith("/auth/refresh") ||
        path.startsWith("/auth/password-reset") ||
        path.startsWith("/commercial/catalog") ||
        path.startsWith("/health") ||
        path.startsWith("/docs") ||
        path.startsWith("/openapi") ||
        path.startsWith("/redoc") ||
        path.startsWith("/internal/bootstrap")
    );
}

interface RetryableRequestConfig extends AxiosRequestConfig {
    _retry?: boolean;
}

let refreshInFlight: Promise<void> | null = null;

export const authNavigation = {
    redirectToLogin(): void {
        if (typeof window === "undefined") {
            return;
        }

        if (window.location.pathname !== "/login") {
            window.location.replace("/login");
        }
    },
};

function clearSessionAndRedirect(): void {
    clearAuthStorage();
    authNavigation.redirectToLogin();
}

async function performRefresh(): Promise<void> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        throw new Error("Missing refresh token");
    }

    const response = await axios.post<TokenResponse>(
        `${API_BASE_URL}/auth/refresh`,
        {
            refresh_token: refreshToken,
        },
        {
            headers: {
                "Content-Type": "application/json",
            },
        },
    );

    updateAuthTokens(response.data.access_token, response.data.refresh_token);
}

function refreshSession(): Promise<void> {
    if (!refreshInFlight) {
        refreshInFlight = performRefresh()
            .catch((error) => {
                clearSessionAndRedirect();
                throw error;
            })
            .finally(() => {
                refreshInFlight = null;
            });
    }

    return refreshInFlight;
}

apiClient.interceptors.request.use((config) => {
    const requestPath = normalizePath(config.url ?? "");
    const accessToken = getAccessToken();
    const tenantId = getTenantId();

    if (!isPublicPath(requestPath) && (!accessToken || !tenantId)) {
        return Promise.reject(
            new AxiosError(
                "Auth context is not ready for this protected request.",
                "ERR_AUTH_CONTEXT_NOT_READY",
                config,
            ),
        );
    }

    const headers = AxiosHeaders.from(config.headers);
    if (accessToken) {
        headers.set("Authorization", `Bearer ${accessToken}`);
    }

    if (tenantId) {
        headers.set("X-Tenant-Id", tenantId);
    }

    config.headers = headers;

    return config;
});

apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        applyNormalizedApiErrorMessage(error);
        const originalRequest = error.config as RetryableRequestConfig | undefined;
        const status = error.response?.status;

        if (status !== 401 || !originalRequest) {
            return Promise.reject(error);
        }

        const requestPath = normalizePath(originalRequest.url ?? "");
        if (isPublicPath(requestPath) || originalRequest._retry) {
            return Promise.reject(error);
        }

        originalRequest._retry = true;

        try {
            await refreshSession();
            return apiClient(originalRequest);
        } catch {
            return Promise.reject(error);
        }
    },
);

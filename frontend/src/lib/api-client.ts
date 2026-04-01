import axios, { AxiosError } from "axios";

import { API_BASE_URL } from "@/constants/env";
import { getAccessToken, getTenantId } from "@/lib/auth-storage";

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
        path.startsWith("/auth/refresh") ||
        path.startsWith("/auth/password-reset") ||
        path.startsWith("/health") ||
        path.startsWith("/docs") ||
        path.startsWith("/openapi") ||
        path.startsWith("/redoc") ||
        path.startsWith("/internal/bootstrap")
    );
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

    if (!config.headers) {
        config.headers = {};
    }

    if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
    }

    if (tenantId) {
        config.headers["X-Tenant-Id"] = tenantId;
    }

    return config;
});

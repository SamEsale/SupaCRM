import {
    ACCESS_TOKEN_KEY,
    AUTH_USER_KEY,
    REFRESH_TOKEN_KEY,
    TENANT_ID_KEY,
} from "@/constants/auth";
import type { AuthState, AuthUser } from "@/types/auth";

function isBrowser(): boolean {
    return typeof window !== "undefined";
}

export function getAccessToken(): string | null {
    if (!isBrowser()) {
        return null;
    }

    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
    if (!isBrowser()) {
        return null;
    }

    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getTenantId(): string | null {
    if (!isBrowser()) {
        return null;
    }

    return window.localStorage.getItem(TENANT_ID_KEY);
}

export function getStoredUser(): AuthUser | null {
    if (!isBrowser()) {
        return null;
    }

    const rawUser = window.localStorage.getItem(AUTH_USER_KEY);

    if (!rawUser) {
        return null;
    }

    try {
        return JSON.parse(rawUser) as AuthUser;
    } catch {
        return null;
    }
}

export function setTenantId(tenantId: string): void {
    if (!isBrowser()) {
        return;
    }

    window.localStorage.setItem(TENANT_ID_KEY, tenantId);
}

export function setTokenStorage(
    accessToken: string,
    refreshToken: string,
): void {
    if (!isBrowser()) {
        return;
    }

    window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function setStoredUser(user: AuthUser): void {
    if (!isBrowser()) {
        return;
    }

    window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

export function setAuthStorage(
    accessToken: string,
    refreshToken: string,
    user: AuthUser,
): void {
    setTokenStorage(accessToken, refreshToken);
    setTenantId(user.tenant_id);
    setStoredUser(user);
}

export function clearAuthStorage(): void {
    if (!isBrowser()) {
        return;
    }

    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.localStorage.removeItem(AUTH_USER_KEY);
    window.localStorage.removeItem(TENANT_ID_KEY);
}

export function getAuthStateFromStorage(): AuthState {
    const accessToken = getAccessToken();
    const refreshToken = getRefreshToken();
    const user = getStoredUser();

    return {
        user,
        accessToken,
        refreshToken,
        isAuthenticated: Boolean(accessToken && refreshToken && user),
    };
}
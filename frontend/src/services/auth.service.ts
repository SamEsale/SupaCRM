import { apiClient } from "@/lib/api-client";
import type {
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    RegisterResponse,
    RefreshTokenRequest,
    TokenResponse,
} from "@/types/auth";

export async function login(payload: LoginRequest): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>("/auth/login", payload);
    return response.data;
}

export async function register(payload: RegisterRequest): Promise<RegisterResponse> {
    const response = await apiClient.post<RegisterResponse>("/auth/register", payload);
    return response.data;
}

export async function refreshAccessToken(
    payload: RefreshTokenRequest,
): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>("/auth/refresh", payload);
    return response.data;
}

export async function logout(
    payload: LogoutRequest,
): Promise<LogoutResponse> {
    const response = await apiClient.post<LogoutResponse>("/auth/logout", payload);
    return response.data;
}

export async function getCurrentUser(
    tenantId: string,
): Promise<CurrentUserResponse> {
    const response = await apiClient.get<CurrentUserResponse>("/auth/whoami", {
        headers: {
            "X-Tenant-Id": tenantId,
        },
    });

    return response.data;
}

export async function requestPasswordReset(
    payload: PasswordResetRequest,
): Promise<PasswordResetResponse> {
    const response = await apiClient.post<PasswordResetResponse>(
        "/auth/password-reset/request",
        payload,
    );
    return response.data;
}

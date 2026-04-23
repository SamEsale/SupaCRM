export type UserRole = "owner" | "admin" | "manager" | "user" | string;

export interface AuthUser {
    user_id: string;
    tenant_id: string;
    email: string;
    full_name: string | null;
    roles: string[];
    is_owner: boolean;
    user_is_active: boolean;
    membership_is_active: boolean;
    tenant_is_active: boolean;
}

export interface LoginRequest {
    tenant_id?: string | null;
    email: string;
    password: string;
}

export interface RegisterRequest {
    company_name: string;
    full_name?: string | null;
    email: string;
    password: string;
    plan_code: string;
    provider: string;
    start_trial: boolean;
}

export interface RefreshTokenRequest {
    refresh_token: string;
}

export interface PasswordResetRequest {
    tenant_id: string;
    email: string;
}

export interface LogoutRequest {
    refresh_token: string;
    revoke_family?: boolean;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    tenant_id: string;
    token_type: string;
    access_token_expires_at: string;
    refresh_token_expires_at: string;
}

export interface RegisterResponse extends TokenResponse {
    tenant_name: string;
    commercial_status: import("@/types/commercial").TenantCommercialStatus;
}

export interface CurrentUserResponse {
    user_id: string;
    tenant_id: string;
    email: string;
    full_name: string | null;
    roles: string[];
    is_owner: boolean;
    user_is_active: boolean;
    membership_is_active: boolean;
    tenant_is_active: boolean;
}

export interface LogoutResponse {
    success: boolean;
}

export interface PasswordResetResponse {
    message: string;
}

export interface AuthState {
    user: AuthUser | null;
    accessToken: string | null;
    refreshToken: string | null;
    isAuthenticated: boolean;
}

export type TenantStatus = "active" | "suspended" | "disabled";

export interface Tenant {
    id: string;
    name: string;
    is_active: boolean;
    status: TenantStatus;
    status_reason: string | null;
    legal_name?: string | null;
    address_line_1?: string | null;
    address_line_2?: string | null;
    city?: string | null;
    state_region?: string | null;
    postal_code?: string | null;
    country?: string | null;
    vat_number?: string | null;
    default_currency?: string | null;
    secondary_currency?: string | null;
    secondary_currency_rate?: string | null;
    secondary_currency_rate_source?: string | null;
    secondary_currency_rate_as_of?: string | null;
    logo_file_key?: string | null;
    brand_primary_color?: string | null;
    brand_secondary_color?: string | null;
    sidebar_background_color?: string | null;
    sidebar_text_color?: string | null;
    created_at: string;
    updated_at: string;
}

export interface TenantUpdateRequest {
    name: string;
    legal_name?: string | null;
    address_line_1?: string | null;
    address_line_2?: string | null;
    city?: string | null;
    state_region?: string | null;
    postal_code?: string | null;
    country?: string | null;
    vat_number?: string | null;
    default_currency: string;
    secondary_currency?: string | null;
    secondary_currency_rate?: string | null;
    brand_primary_color?: string | null;
    brand_secondary_color?: string | null;
    sidebar_background_color?: string | null;
    sidebar_text_color?: string | null;
}

export interface TenantCommercialSubscription {
    id: string;
    plan_code: string;
    plan_name: string;
    commercial_state: string;
    plan_features: {
        tier?: string;
        self_service?: boolean;
        included_capabilities?: string[];
        launch_limitations?: string[];
    };
    trial_end_at: string | null;
    current_period_end_at: string | null;
    grace_end_at: string | null;
    canceled_at: string | null;
}

export interface TenantOnboardingSummary {
    tenant: Tenant;
    commercial_subscription: TenantCommercialSubscription | null;
    users_total: number;
    owner_count: number;
    admin_count: number;
    bootstrap_complete: boolean;
    ready_for_use: boolean;
    missing_steps: string[];
    warnings: string[];
    next_action: string;
}

export interface TenantUserProvisionRequest {
    email: string;
    full_name: string | null;
    password: string | null;
    role_names: string[];
    is_owner: boolean;
}

export interface TenantRole {
    id: string;
    name: string;
    permission_codes: string[];
    created_at: string;
}

export interface TenantUser {
    user_id: string;
    email: string;
    full_name: string | null;
    user_is_active: boolean;
    membership_is_active: boolean;
    is_owner: boolean;
    role_names: string[];
    membership_created_at: string;
}

export interface TenantUserProvisionResponse {
    tenant_id: string;
    user_id: string;
    email: string;
    created_user: boolean;
    created_credentials: boolean;
    password_set: boolean;
    created_membership: boolean;
    is_owner: boolean;
    assigned_roles: string[];
    created_role_assignments: string[];
}

export interface TenantRoleAssignmentRequest {
    role_names: string[];
    is_owner: boolean;
}

export interface TenantRoleAssignmentBatchResponse {
    tenant_id: string;
    user_id: string;
    is_owner: boolean;
    assigned_roles: string[];
    created_role_assignments: string[];
}

export interface TenantMembershipUpdateRequest {
    membership_is_active?: boolean;
    is_owner?: boolean;
    transfer_owner_from_user_id?: string | null;
}

export interface TenantMembershipMutationResponse {
    tenant_id: string;
    user_id: string;
    membership_is_active: boolean;
    is_owner: boolean;
    transferred_owner_from_user_id: string | null;
}

export interface TenantMembershipRemovalResponse {
    tenant_id: string;
    user_id: string;
    removed: boolean;
}

export interface TenantStatusUpdateRequest {
    status: TenantStatus;
    status_reason?: string | null;
}

export interface CommercialSubscriptionStartRequest {
    plan_code: string;
    provider: string;
    start_trial: boolean;
    customer_email?: string | null;
    customer_name?: string | null;
}

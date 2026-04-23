export interface RecentAuditActivity {
    id: string;
    action: string;
    resource: string | null;
    resource_id: string | null;
    status_code: number | null;
    message: string | null;
    actor_user_id: string | null;
    actor_full_name: string | null;
    actor_email: string | null;
    created_at: string;
}

export interface RecentAuditActivityListResponse {
    items: RecentAuditActivity[];
    total: number;
}

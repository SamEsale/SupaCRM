export interface BuildLoginPayloadOptions {
    isLocalLogin: boolean;
    tenantId: string;
    email: string;
    password: string;
}

export function buildLoginRequestPayload({
    isLocalLogin,
    tenantId,
    email,
    password,
}: BuildLoginPayloadOptions): {
    tenant_id?: string;
    email: string;
    password: string;
} {
    const normalizedTenantId = tenantId.trim();
    const shouldSendTenantId = !isLocalLogin || normalizedTenantId.length > 0;

    const payload: {
        tenant_id?: string;
        email: string;
        password: string;
    } = {
        email: email.trim(),
        password,
    };

    if (shouldSendTenantId) {
        payload.tenant_id = normalizedTenantId;
    }

    return payload;
}

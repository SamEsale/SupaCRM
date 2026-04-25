# Auth and Tenant Context Model

This document describes the tenant-aware auth contract used by SupaCRM after login hardening.

## Core Rules

- Access tokens always include `sub` and `tenant_id`.
- Refresh tokens also include `sub` and `tenant_id`.
- The backend is the source of truth for tenant authorization.
- The frontend stores the authenticated user profile and treats `user.tenant_id` as the canonical tenant source for request headers.
- If the raw tenant key and the stored user disagree, the stored user wins. The raw tenant key is compatibility storage only.
- In non-production, the backend may infer a tenant from email only when the email matches exactly one active tenant.
- In production, `/auth/login` requires an explicit `tenant_id`.

## Login Flow

### Local / Dev

1. The login page on `localhost` hides the tenant field.
2. The frontend submits `email + password` only.
3. The backend resolves the tenant from the email when exactly one active tenant exists.
4. The login response returns `tenant_id`.
5. The frontend stores the resolved user/profile state and uses the resolved tenant for subsequent requests.

### Production

1. The login page requires a tenant id.
2. `/auth/login` fails closed if `tenant_id` is missing.
3. The backend validates the tenant, membership, and password before issuing tokens.

## Token Claims

Access token claims:

- `sub`
- `tenant_id`
- `roles`
- `jti`
- `typ=access`
- `iat`
- `exp`
- `iss`
- `aud`

Refresh token claims:

- `sub`
- `tenant_id`
- `token_version`
- `family_id`
- `jti`
- `typ=refresh`
- `iat`
- `exp`
- `iss`
- `aud`

## Post-Login Request Rules

- Protected requests must send `Authorization: Bearer <access_token>`.
- Protected requests must send `X-Tenant-Id`.
- The backend rejects requests when the header tenant does not match the token tenant.
- Protected requests fail closed if the user, membership, or tenant is inactive.
- Tenant switching by header manipulation alone is not allowed.

## Frontend Storage

- The frontend keeps the signed-in user profile in local storage.
- `user.tenant_id` is the canonical tenant source.
- The raw tenant key is treated as compatibility storage and should never override the authenticated user profile.
- Logout clears all auth-scoped state.

## Common Failure Modes

- Missing tenant id in production login.
- Ambiguous email in local/dev login when the same email belongs to multiple active tenants.
- Missing `X-Tenant-Id` on protected routes.
- Header tenant mismatch.
- Inactive user or membership.

## Why This Is Safe

- Production does not infer tenant context.
- Protected requests fail closed instead of falling back to a guessed tenant.
- The token, header, and database membership checks all need to agree before a protected request succeeds.
- Local convenience exists only for the single-tenant local bootstrap flow and is explicitly disabled in production.

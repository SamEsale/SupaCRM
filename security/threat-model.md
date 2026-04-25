# Threat Model

# Threat Model (High-level)

## Assets to protect
- Tenant business data (CRM contacts, invoices, payments metadata, tickets)
- Authentication material (password hashes, refresh tokens)
- API credentials for integrations (Stripe, email provider, WhatsApp, FX API)
- Audit logs (integrity and completeness)
- Object storage (MinIO) tenant-separated data

## Key trust boundaries
- Internet client -> Nginx/API Gateway -> FastAPI backend
- Backend -> Postgres (RLS enforced)
- Backend/Workers -> Redis queue
- Backend -> External providers (Stripe, WhatsApp, email)
- Backend -> MinIO presigned URLs

## Highest-risk abuse cases (must mitigate)
1. Cross-tenant data access
   - Causes: missing tenant context, broken RLS policy, unsafe JOINs, admin endpoints bypass.
   - Required mitigations:
     - Postgres RLS enabled on every tenant-owned table.
     - All queries include tenant scope.
     - Automated tests: ensure cross-tenant reads/writes are blocked.
     - DB session sets tenant context and RLS policies enforce it.

2. Token theft and session hijacking
   - Causes: long-lived tokens, insecure storage, missing refresh rotation, lack of revocation.
   - Required mitigations:
     - Short-lived access JWT.
     - Refresh token rotation + server-side token versioning/revocation.
     - Secure cookie strategy if browser-based (HttpOnly, SameSite, Secure) OR secure storage patterns.

3. Webhook spoofing / replay (Stripe and others)
   - Causes: missing signature verification, accepting old timestamps, non-idempotent processing.
   - Required mitigations:
     - Signature verification for every webhook.
     - Replay protection (timestamp tolerance) where supported.
     - Idempotency keys + store processed event IDs.

4. Object storage data bleed (MinIO)
   - Causes: non-tenant-scoped keys, overly broad bucket policies, long-lived presigned URLs.
   - Required mitigations:
     - Tenant namespace per object key/prefix.
     - Presigned URLs short TTL.
     - Validate object keys/prefixes server-side.

5. Privilege escalation in RBAC
   - Causes: role changes without audit, missing tenant-scope checks, unsafe admin endpoints.
   - Required mitigations:
     - Tenant-scoped RBAC checks.
     - Audit logging for permission/role changes.
     - Separate super-admin plane from tenant-admin.

## Assumptions
- Backend is the authority for tenancy enforcement.
- Postgres RLS is mandatory for tenant-owned data.
- Monitoring and audit logging exist for privileged operations.

## Security test requirements (minimum)
- Cross-tenant isolation tests for each tenant-owned resource
- Webhook signature verification tests
- Refresh token rotation tests
- Presigned URL TTL and namespace validation tests


# Data Protection


# Data Protection Policy

## Tenant isolation
- Postgres RLS enforced for all tenant-owned tables.
- Every tenant-owned table must include:
  - `tenant_id` (indexed)
  - created/updated timestamps

## Encryption
- In transit: TLS termination at Nginx/load balancer; internal TLS where feasible.
- At rest: database disk encryption (cloud provider or OS-level).
- Application-level encryption: only for highly sensitive fields if required by compliance.

## Storage (MinIO)
- Object keys must include tenant namespace/prefix.
- Presigned URLs:
  - short TTL
  - scoped to the exact object
  - generated only after verifying tenant authorization

## Logging and audit
- Logs must not contain secrets or sensitive personal data.
- Privileged operations must generate audit events (user/tenant/action/entity/timestamp).

## Retention
- Define tenant data retention policy (future: configurable per tenant).
- Audit logs: append-only, retain per compliance needs (minimum 90 days recommended for MVP unless regulated otherwise).

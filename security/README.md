# Security (SupaCRM)

This directory contains security baselines, threat model, and operational policies for SupaCRM.

## Scope
- Multi-tenant SaaS controls (tenant isolation, RLS, tenancy context propagation)
- Authentication and authorization (JWT, refresh tokens, RBAC)
- Data protection (encryption, retention, logging, audit trails)
- Supply-chain security (dependency scanning, SAST, container scanning)
- Operational security (secrets rotation, incident response references)

## Non-goals
- This folder does not store secrets.
- This folder does not replace runtime controls; it documents them and defines required engineering practices.

## Ownership
Engineering owns implementation; Security/Compliance (if applicable) reviews.


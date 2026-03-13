# RBAC Model


# RBAC Model (Tenant-scoped)

## Core rules
- Every permission check is tenant-scoped.
- A user may belong to one tenant context per request.
- Super-admin capabilities must be isolated from tenant-admin.

## Suggested roles
Tenant roles:
- `tenant_admin`
- `sales_manager`
- `sales_rep`
- `accounting_user`
- `support_agent`
- `marketing_user`
- `read_only`

Platform roles (global):
- `super_admin` (platform operator only)

## Permission categories
- tenants: manage tenant users, roles, settings
- crm: contacts, companies, notes
- sales: opportunities, pipelines
- invoicing: invoices, credit notes
- payments: subscriptions, payment methods
- support: tickets, KB articles
- marketing: campaigns
- admin: settings, integrations config

## Change control
- Role/permission changes MUST be audit logged (who/when/what).
- Prevent tenant_admin from granting super_admin.
- Prevent permission escalation via API (validate server-side).

## API requirements
- Endpoints must declare required permissions.
- Service layer must enforce permission checks (not only routes).

# Security Surface Audit

This audit records the current production exposure of unfinished or partially wired modules.

## Reviewed modules

- marketing
- payments
- accounting
- reporting
- support
- workers
- admin/settings
- debug
- internal bootstrap

## Findings

- `marketing`, `payments`, and `accounting` do not appear to be mounted on the public API router.
- `reporting` and `support` are mounted behind the active-tenant router and require explicit permissions.
- `workers` do not expose HTTP routes.
- `admin` has no mounted public router in the API surface.
- `debug` exposes `/debug/rbac`, but this is now disabled in production builds by router gating.
- `internal/bootstrap` remains mounted but requires the bootstrap key and is intended for controlled internal operations.

## Tightening completed

- Production API router mounting now excludes the debug router when `ENV=prod` or `DEBUG=false`.

## Intentionally not production-enabled

- `debug` remains available only outside production.
- Unfinished modules without public routers remain unmounted rather than being stubbed into the production API.

## Notes for future reviews

- Re-run this audit whenever new routers are added or mounted.
- Re-check public exposure whenever a module moves from placeholder to real business logic.

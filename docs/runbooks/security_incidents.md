# Security Incident Response

This runbook focuses on the auth-abuse signals now emitted by SupaCRM.

## Signals to watch

- `auth.rate_limit.exceeded`
- `auth.rate_limit.exceeded.suspected`
- `auth.login.failed`
- `auth.login.failed.suspected`
- `auth.login.locked`

Each security event is emitted as a structured JSON log line on stdout/stderr.

## Detection workflow

1. Query logs for `logger="supacrm.security"`.
2. Group by `tenant_id`, `ip_address`, and `scope`.
3. Look for repeated `attempt_count` growth or repeated `auth.rate_limit.exceeded`.
4. Verify whether a lockout event was triggered for the user.

## Immediate response

- Confirm whether the source IP is legitimate.
- If abuse is confirmed, block the source at the edge or upstream security layer.
- If the tenant shows a burst of failed logins, consider rotating credentials or disabling the impacted account.
- If a tenant is under active attack, temporarily suspend the tenant lifecycle using the bootstrap/admin controls.

## Operational validation

- Confirm `/ready` still returns healthy after mitigation changes.
- Confirm auth requests continue to return correct 401/429 outcomes.
- Confirm the security event stream is still present in stdout logs and Loki.

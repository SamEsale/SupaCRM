# Edge Security Baseline

This runbook documents the production nginx edge baseline for SupaCRM.

## Enforced now

- `client_max_body_size` is capped at 20 MB.
- Auth endpoints are method-restricted:
  - `POST /api/auth/login`
  - `POST /api/auth/refresh`
  - `POST /api/auth/logout`
  - `GET /api/auth/whoami`
- Edge rate limiting is enabled for auth and API requests.
- Obvious traversal-style URI patterns such as `../` and encoded equivalents are rejected.
- Forwarded headers are preserved for backend proxy awareness:
  - `X-Forwarded-For`
  - `X-Forwarded-Proto`
  - `X-Forwarded-Port`
  - `X-Request-ID`

## Enforced later at CDN/WAF

This nginx layer is not a full CDN/WAF.

Later hardening should add:

- ASN / geo policy
- bot reputation / challenge policy
- distributed IP reputation feeds
- per-route bot scoring
- broader request anomaly detection at the edge

## Operational checks

- Verify nginx config syntax before rollout.
- Confirm `/health` and `/ready` still work through the public edge.
- Confirm auth 429s are still observed at the backend when edge limits are exceeded.

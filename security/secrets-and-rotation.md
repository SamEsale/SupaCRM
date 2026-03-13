# Secrets and Rotation



# Secrets and Rotation Policy

## Principles
- Never commit secrets to Git.
- Prefer short-lived credentials and scoped API keys.
- Rotate secrets on a defined cadence and immediately after suspected exposure.

## Secret sources
- Local development: `.env` (not committed), derived from `.env.example`
- Staging/Production: secret manager (preferred) or CI/CD injected env vars

## Required secrets (examples)
- `DATABASE_URL`
- `JWT_SECRET` / signing keys
- `REFRESH_TOKEN_SECRET` (if separate)
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- MinIO: `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- Email provider API keys
- WhatsApp Business tokens

## Rotation cadence (minimum baseline)
- JWT signing keys: every 90 days or on incident
- Stripe webhook secret: rotate on incident and annually if feasible
- MinIO keys: every 90–180 days
- Email provider keys: every 90–180 days

## Operational requirements
- Keys must be scoped to least privilege.
- Maintain break-glass procedures for production access.
- Document rotation steps in `docs/runbooks/` (see runbooks folder when added).

## Logging
- Secrets must never appear in logs.
- Configure log scrubbing where applicable.


# Scaling Runbook

This runbook documents the first production scaling slice for the stable SupaCRM surface.

## What is scaled now

- Protected request validation uses a short-lived Redis auth cache.
- `/auth/whoami` uses a short-lived Redis profile cache.
- Login and refresh enqueue cache warmup jobs.
- Logout and password reset invalidate affected cache entries.
- A dedicated RQ worker service processes cache maintenance jobs.

## What is intentionally staged

- No autoscaling policy yet.
- No distributed task fan-out beyond auth cache maintenance.
- No queue-backed CRM/sales/reporting batch jobs yet.

## Operational notes

- If Redis is unavailable, the application falls back to DB-backed validation.
- Cache entries are intentionally short-lived so request correctness still comes from the database on cache miss.
- Restart the worker if queue jobs stop processing or Redis has been restarted.

## Validation

- Confirm the `worker` service is healthy in `docker compose -f infrastructure/docker-compose.prod.yml ps`.
- Log in once and confirm subsequent protected requests are served from the cache path by checking the request timing / cache logs.
- Use the auth whoami route after login to verify the profile cache is populated.

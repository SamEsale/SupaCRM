# Stripe Billing Runbook

This runbook covers the Stripe-backed commercial subscription slice that is currently implemented in SupaCRM.

## Configuration expectations

Stripe webhook verification is performed at the backend edge with the environment variable `STRIPE_WEBHOOK_SECRET`.

The tenant payment gateway record must also be configured for Stripe readiness:

- `is_enabled=true`
- `mode=test` or `mode=live`
- `publishable_key`
- `secret_key`
- `webhook_secret`

The tenant-scoped record is what the commercial service uses for provider operations and readiness checks. The global env webhook secret is what the `/commercial/webhooks/stripe` route uses to verify the incoming Stripe signature before any local processing happens.

## Migration and schema verification

From the repo root:

```bash
./backend/.venv313/bin/python -m alembic -c backend/alembic.ini heads
./backend/.venv313/bin/python -m alembic -c backend/alembic.ini current
./backend/.venv313/bin/python -m alembic -c backend/alembic.ini upgrade head
```

The commercial Stripe lifecycle in this repo uses these existing tables:

- `commercial_subscriptions`
- `commercial_billing_cycles`
- `commercial_billing_events`
- `commercial_payment_methods`

Do not create parallel billing tables for production verification. The billing event ledger is already the replay and diagnosis source in this slice.

## Test-mode verification flow

1. Confirm Stripe gateway readiness for the tenant in the UI:
- `Finance -> Payments -> Gateway Settings`
- `Finance -> Payments -> Provider Foundation`

2. Confirm the backend edge is using the correct signing secret:
- `STRIPE_WEBHOOK_SECRET` is set in the backend environment
- Stripe is posting to `/commercial/webhooks/stripe`

3. Capture a payment method in test mode:
- open `Finance -> Payments -> Subscription Billing`
- use `Add Payment Method` or `Update Payment Method`
- complete the Stripe setup checkout with a Stripe test card

4. Create or advance the subscription through the existing UI path:
- use `Start Trial` for a new tenant trial
- use `Start Subscription` for the first paid start
- use `Convert Trial To Paid` only when the tenant is already in a Stripe-backed trial state

5. Confirm the resulting tenant state in SupaCRM:
- `Subscription Billing` page shows the grounded Stripe status
- recent billing events include the latest Stripe event IDs
- recent billing events do not show `processing_status=failed`

## Replay and idempotency expectations

The billing event ledger is keyed by `(provider, external_event_id)` in `commercial_billing_events`.

Expected behavior:

- a Stripe event that has already been processed should remain processed on duplicate delivery
- duplicate delivery must not re-run the local mutation after the event is already processed
- a failed event can be replayed after the code or configuration issue is fixed
- failed processing rolls back the local subscription/payment-method mutation and records the failure in `commercial_billing_events`

Use Stripe test-mode replay tools or the Stripe dashboard resend action when validating recovery after a fix.

## How to verify tenant billing state after events

UI checks:

- `Finance -> Payments -> Subscription Billing`
- `Current subscription`
- `Recent billing events`

Database checks:

```sql
select tenant_id, commercial_state, subscription_status, provider_customer_id, provider_subscription_id, grace_end_at
from public.commercial_subscriptions
where tenant_id = '<tenant-id>';

select provider, external_event_id, event_type, processing_status, action_taken, error_message, created_at, processed_at
from public.commercial_billing_events
where tenant_id = '<tenant-id>'
order by created_at desc
limit 20;

select provider_payment_method_id, is_default, is_active, card_brand, card_last4, updated_at
from public.commercial_payment_methods
where tenant_id = '<tenant-id>'
order by is_default desc, updated_at desc;
```

Truthful state mapping in this slice:

- `payment method missing`
- `pending`
- `trialing`
- `active`
- `past_due`
- `canceled`

## Diagnosing failed webhook processing

When a webhook fails:

1. Look at `commercial_billing_events.error_message` for the exact recorded failure.
2. Confirm the event payload shape matches the event type being processed.
3. Confirm the tenant Stripe gateway record is still configured and enabled.
4. Confirm the backend env `STRIPE_WEBHOOK_SECRET` matches the Stripe endpoint signing secret.
5. Confirm the subscription can actually be resolved from Stripe metadata, customer ID, or provider subscription ID.

If the event remains failed after a code or config fix:

- replay the same Stripe event in test mode
- confirm the existing `commercial_billing_events` row moves from `failed` to `processed`
- confirm the tenant commercial state changes only after the replay succeeds

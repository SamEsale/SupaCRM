from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json

import pytest

from app.commercial.providers.stripe import StripeCommercialProvider


def _signature_for(secret: str, payload: bytes, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    return hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_parse_webhook_event_uses_subscription_object_id_and_ignores_non_dict_metadata() -> None:
    provider = StripeCommercialProvider(webhook_secret="whsec_test")
    payload = json.dumps(
        {
            "id": "evt_123",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_provider_123",
                    "customer": "cus_123",
                    "metadata": ["unexpected-shape"],
                }
            },
        }
    ).encode("utf-8")

    event = await provider.parse_webhook_event(payload=payload)

    assert event.event_id == "evt_123"
    assert event.event_type == "customer.subscription.updated"
    assert event.customer_id == "cus_123"
    assert event.subscription_id == "sub_provider_123"


@pytest.mark.asyncio
async def test_verify_webhook_signature_accepts_matching_signature_and_rejects_stale_replay() -> None:
    secret = "whsec_test"
    provider = StripeCommercialProvider(webhook_secret=secret)
    payload = json.dumps({"id": "evt_123", "type": "invoice.payment_succeeded"}).encode("utf-8")

    fresh_timestamp = int(datetime.now(timezone.utc).timestamp())
    fresh_signature = _signature_for(secret, payload, fresh_timestamp)

    assert await provider.verify_webhook_signature(
        payload=payload,
        headers={"stripe-signature": f"t={fresh_timestamp},v1=bad,v1={fresh_signature}"},
    )

    stale_timestamp = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
    stale_signature = _signature_for(secret, payload, stale_timestamp)

    assert not await provider.verify_webhook_signature(
        payload=payload,
        headers={"stripe-signature": f"t={stale_timestamp},v1={stale_signature}"},
    )

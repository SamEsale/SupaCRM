from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import json
from typing import Any

import httpx

from app.core.config import settings
from app.commercial.providers.base import (
    CommercialCheckoutSessionResult,
    CommercialProvider,
    CommercialProviderSubscriptionResult,
    CommercialWebhookEvent,
)


class StripeCommercialProvider(CommercialProvider):
    BASE_URL = "https://api.stripe.com/v1"
    DEFAULT_WEBHOOK_TOLERANCE = timedelta(minutes=5)

    def __init__(
        self,
        *,
        api_key: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self.api_key = (api_key or settings.STRIPE_API_KEY or "").strip()
        self.webhook_secret = (webhook_secret or settings.STRIPE_WEBHOOK_SECRET or "").strip()

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("STRIPE_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _to_optional_string(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    async def create_customer(
        self,
        *,
        email: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {"email": email}
        for key, value in (metadata or {}).items():
            payload[f"metadata[{key}]"] = str(value)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/customers",
                headers=self._headers(),
                data=payload,
            )
            response.raise_for_status()
            return response.json()["id"]

    async def create_subscription(
        self,
        *,
        customer_id: str,
        price_id: str,
        metadata: dict[str, Any] | None = None,
        trial_days: int = 0,
    ) -> CommercialProviderSubscriptionResult:
        payload: dict[str, Any] = {
            "customer": customer_id,
            "items[0][price]": price_id,
            "payment_behavior": "default_incomplete",
            "collection_method": "charge_automatically",
        }
        if trial_days > 0:
            payload["trial_period_days"] = trial_days
        for key, value in (metadata or {}).items():
            payload[f"metadata[{key}]"] = str(value)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/subscriptions",
                headers=self._headers(),
                data=payload,
            )
            response.raise_for_status()
            data = response.json()
        return CommercialProviderSubscriptionResult(
            provider="stripe",
            provider_customer_id=data.get("customer"),
            provider_subscription_id=data.get("id"),
            status=str(data.get("status") or "trial"),
            trial_end_at=self._to_datetime(data.get("trial_end")),
            current_period_start_at=self._to_datetime(data.get("current_period_start")),
            current_period_end_at=self._to_datetime(data.get("current_period_end")),
            cancel_at_period_end=bool(data.get("cancel_at_period_end")),
            raw=data,
        )

    async def cancel_subscription(
        self,
        *,
        subscription_id: str,
        cancel_at_period_end: bool = False,
    ) -> CommercialProviderSubscriptionResult:
        payload = {"cancel_at_period_end": str(cancel_at_period_end).lower()}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/subscriptions/{subscription_id}",
                headers=self._headers(),
                data=payload,
            )
            response.raise_for_status()
            data = response.json()
        return CommercialProviderSubscriptionResult(
            provider="stripe",
            provider_customer_id=data.get("customer"),
            provider_subscription_id=data.get("id"),
            status=str(data.get("status") or "active"),
            trial_end_at=self._to_datetime(data.get("trial_end")),
            current_period_start_at=self._to_datetime(data.get("current_period_start")),
            current_period_end_at=self._to_datetime(data.get("current_period_end")),
            cancel_at_period_end=bool(data.get("cancel_at_period_end")),
            raw=data,
        )

    async def verify_webhook_signature(self, *, payload: bytes, headers: dict[str, str]) -> bool:
        if not self.webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")

        signature_header = headers.get("stripe-signature") or headers.get("Stripe-Signature")
        if not signature_header:
            return False

        timestamp: str | None = None
        signatures: list[str] = []
        for part in signature_header.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                normalized_key = key.strip()
                normalized_value = value.strip()
                if normalized_key == "t":
                    timestamp = normalized_value
                elif normalized_key == "v1" and normalized_value:
                    signatures.append(normalized_value)
        if not timestamp or not signatures:
            return False

        try:
            payload_text = payload.decode("utf-8")
            signed_at = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        except (UnicodeDecodeError, ValueError, OSError):
            return False

        if abs((datetime.now(timezone.utc) - signed_at).total_seconds()) > self.DEFAULT_WEBHOOK_TOLERANCE.total_seconds():
            return False

        signed_payload = f"{timestamp}.{payload_text}".encode("utf-8")
        expected = hmac.new(
            self.webhook_secret.encode(),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        return any(hmac.compare_digest(signature, expected) for signature in signatures)

    async def parse_webhook_event(self, *, payload: bytes) -> CommercialWebhookEvent:
        try:
            data = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Stripe webhook payload is not valid JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("Stripe webhook payload must be a JSON object")

        raw_data = self._as_dict(data.get("data"))
        payload_object = self._as_dict(raw_data.get("object"))
        metadata = self._as_dict(payload_object.get("metadata"))
        event_id = self._to_optional_string(data.get("id"))
        event_type = self._to_optional_string(data.get("type"))
        if not event_id or not event_type:
            raise ValueError("Stripe webhook payload is missing id or type")

        normalized_type = event_type.lower()
        customer_id = self._to_optional_string(
            metadata.get("customer_id") or payload_object.get("customer")
        )
        subscription_id = self._to_optional_string(
            metadata.get("subscription_id") or payload_object.get("subscription")
        )
        if not subscription_id and normalized_type.startswith("customer.subscription."):
            subscription_id = self._to_optional_string(payload_object.get("id"))

        return CommercialWebhookEvent(
            provider="stripe",
            event_id=event_id,
            event_type=event_type,
            raw_payload=data,
            customer_id=customer_id,
            subscription_id=subscription_id,
        )

    async def get_payment_method(
        self,
        *,
        payment_method_id: str,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/payment_methods/{payment_method_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def attach_payment_method(
        self,
        *,
        customer_id: str,
        payment_method_id: str,
    ) -> dict[str, Any]:
        payload = {"customer": customer_id}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/payment_methods/{payment_method_id}/attach",
                headers=self._headers(),
                data=payload,
            )
            response.raise_for_status()
            return response.json()

    async def detach_payment_method(
        self,
        *,
        payment_method_id: str,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/payment_methods/{payment_method_id}/detach",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def list_payment_methods(
        self,
        *,
        customer_id: str,
        type: str = "card",
    ) -> list[dict[str, Any]]:
        params = {"customer": customer_id, "type": type}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/payment_methods",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    async def set_default_payment_method(
        self,
        *,
        customer_id: str,
        payment_method_id: str,
    ) -> dict[str, Any]:
        payload = {"invoice_settings[default_payment_method]": payment_method_id}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/customers/{customer_id}",
                headers=self._headers(),
                data=payload,
            )
            response.raise_for_status()
            return response.json()

    async def update_subscription(
        self,
        *,
        subscription_id: str,
        price_id: str | None = None,
        items: list[dict[str, Any]] | None = None,
        trial_end_at_now: bool = False,
        prorate: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> CommercialProviderSubscriptionResult:
        payload: dict[str, Any] = {}

        if items:
            for idx, item in enumerate(items):
                for key, value in item.items():
                    payload[f"items[{idx}][{key}]"] = value
        elif price_id:
            payload["items[0][price]"] = price_id

        if trial_end_at_now:
            payload["trial_end"] = "now"

        payload["proration_behavior"] = "create_prorations" if prorate else "none"

        for key, value in (metadata or {}).items():
            payload[f"metadata[{key}]"] = str(value)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/subscriptions/{subscription_id}",
                headers=self._headers(),
                data=payload,
            )
            response.raise_for_status()
            data = response.json()

        return CommercialProviderSubscriptionResult(
            provider="stripe",
            provider_customer_id=data.get("customer"),
            provider_subscription_id=data.get("id"),
            status=str(data.get("status") or "active"),
            trial_end_at=self._to_datetime(data.get("trial_end")),
            current_period_start_at=self._to_datetime(data.get("current_period_start")),
            current_period_end_at=self._to_datetime(data.get("current_period_end")),
            cancel_at_period_end=bool(data.get("cancel_at_period_end")),
            raw=data,
        )

    async def create_checkout_session(
        self,
        *,
        mode: str,
        success_url: str,
        cancel_url: str,
        customer_id: str | None = None,
        customer_email: str | None = None,
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CommercialCheckoutSessionResult:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"setup", "subscription"}:
            raise ValueError(f"Unsupported Stripe checkout mode: {mode}")

        payload: dict[str, Any] = {
            "mode": normalized_mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "payment_method_types[0]": "card",
        }
        if customer_id:
            payload["customer"] = customer_id
        elif customer_email:
            payload["customer_email"] = customer_email

        if normalized_mode == "subscription":
            if not price_id:
                raise ValueError("Stripe checkout subscription mode requires a price_id")
            payload["line_items[0][price]"] = price_id
            payload["line_items[0][quantity]"] = "1"

        for key, value in (metadata or {}).items():
            payload[f"metadata[{key}]"] = str(value)
            if normalized_mode == "subscription":
                payload[f"subscription_data[metadata][{key}]"] = str(value)
            if normalized_mode == "setup":
                payload[f"setup_intent_data[metadata][{key}]"] = str(value)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/checkout/sessions",
                headers=self._headers(),
                data=payload,
            )
            response.raise_for_status()
            data = response.json()

        return CommercialCheckoutSessionResult(
            provider="stripe",
            session_id=str(data["id"]),
            url=str(data["url"]),
            mode=normalized_mode,
            provider_customer_id=data.get("customer"),
            provider_subscription_id=data.get("subscription"),
            raw=data,
        )

    async def get_setup_intent(
        self,
        *,
        setup_intent_id: str,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/setup_intents/{setup_intent_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

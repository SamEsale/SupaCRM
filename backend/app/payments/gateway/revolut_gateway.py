# backend/app/payments/gateway/revolut_gateway.py

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel

from .base_gateway import (
    BasePaymentGateway,
    GatewayCustomer,
    PaymentIntent,
    PaymentRefund,
    PaymentStatus,
    WebhookEvent,
    GatewayException,
)


class RevolutGatewayConfig(BaseModel):
    """Configuration required for Revolut Business API."""
    api_key: str
    webhook_secret: str
    base_url: str = "https://merchant.revolut.com/api/1.0"


class RevolutGateway(BasePaymentGateway):
    """
    Revolut Business gateway implementation.

    Docs:
    https://revolut-engineering.github.io/api-docs/business-api/
    """

    def __init__(self, config: RevolutGatewayConfig):
        self.config = config
        self.base_url = config.base_url
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=self.headers, json=payload)
        except Exception as exc:
            raise GatewayException(f"Revolut API error: {exc}") from exc

        if response.status_code >= 400:
            raise GatewayException(
                f"Revolut API Error {response.status_code}: {response.text}"
            )

        return response.json()

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=self.headers)
        except Exception as exc:
            raise GatewayException(f"Revolut API error: {exc}") from exc

        if response.status_code >= 400:
            raise GatewayException(
                f"Revolut API Error {response.status_code}: {response.text}"
            )

        return response.json()

    # -------------------------------------------------------------------------
    # Abstract Method Implementations
    # -------------------------------------------------------------------------

    async def create_customer(
        self, *, email: str, name: Optional[str] = None, metadata: Optional[dict] = None
    ) -> GatewayCustomer:
        """
        Revolut does not create standalone customer records like Stripe.
        Instead, we simulate a "customer object" internally.
        """
        customer_id = hashlib.sha256(email.encode()).hexdigest()[:32]  # deterministic

        return GatewayCustomer(
            id=customer_id,
            email=email,
            name=name,
            metadata=metadata or {},
            raw_response={"generated": True, "source": "email_hash"},
        )

    async def create_payment_intent(
        self,
        *,
        amount: int,
        currency: str,
        customer_id: Optional[str],
        metadata: Optional[dict] = None
    ) -> PaymentIntent:
        payload = {
            "amount": amount,
            "currency": currency,
            "capture_mode": "AUTOMATIC",
            "merchant_order_ext_ref": customer_id or "guest",
            "description": metadata.get("description") if metadata else None,
        }

        data = await self._post("/orders", payload)

        return PaymentIntent(
            id=data["id"],
            amount=amount,
            currency=currency,
            customer_id=customer_id,
            status=PaymentStatus.REQUIRES_ACTION,
            raw_response=data,
        )

    async def refund_payment(
        self, *, transaction_id: str, amount: Optional[int] = None, reason: Optional[str] = None
    ) -> PaymentRefund:
        payload = {
            "amount": amount,
            "reason": reason,
        }

        data = await self._post(f"/orders/{transaction_id}/refund", payload)

        return PaymentRefund(
            id=data["id"],
            transaction_id=transaction_id,
            amount=amount,
            raw_response=data,
        )

    async def get_transaction_status(self, *, transaction_id: str) -> PaymentStatus:
        data = await self._get(f"/orders/{transaction_id}")

        revolut_status = data.get("state")

        # Revolut → Generic status mapping
        mapping = {
            "completed": PaymentStatus.SUCCEEDED,
            "authorized": PaymentStatus.REQUIRES_CAPTURE,
            "pending": PaymentStatus.PENDING,
            "failed": PaymentStatus.FAILED,
            "reverted": PaymentStatus.REFUNDED,
        }

        return mapping.get(revolut_status, PaymentStatus.UNKNOWN)

    # -------------------------------------------------------------------------
    # Webhook handling
    # -------------------------------------------------------------------------

    async def verify_webhook_signature(
        self, *, payload: bytes, header_signature: str
    ) -> bool:
        """
        Revolut uses HMAC-SHA256 signatures for webhook verification.
        """
        expected = hmac.new(
            self.config.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, header_signature)

    async def parse_webhook_event(
        self, *, payload: dict
    ) -> WebhookEvent:
        event_type = payload.get("event")
        data = payload.get("data", {})

        return WebhookEvent(
            id=str(payload.get("id")),
            type=event_type,
            data=data,
            raw=payload,
        )

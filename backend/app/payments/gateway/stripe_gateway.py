# File: backend/app/payments/gateway/stripe_gateway.py

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional

import httpx

from .base_gateway import (
    BasePaymentGateway,
    PaymentCustomer,
    PaymentIntent,
    PaymentRefund,
    PaymentTransactionStatus,
)


class StripeGateway(BasePaymentGateway):
    """
    Implementation of the BasePaymentGateway for Stripe.

    Notes:
    - Uses async HTTP requests (httpx)
    - Must map Stripe's objects to platform-standard models
    - Webhook verification follows Stripe signature spec:
      https://stripe.com/docs/webhooks/signatures
    """

    BASE_URL = "https://api.stripe.com/v1"

    # -------------------------------------------------------------------------
    # Helper: Stripe authorization header
    # -------------------------------------------------------------------------
    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    # -------------------------------------------------------------------------
    # 1. Create Customer
    # -------------------------------------------------------------------------
    async def create_customer(
        self,
        email: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentCustomer:

        data = {
            "email": email,
        }

        if metadata:
            # Stripe requires metadata.* flattened fields
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = str(v)

        response = await self._request(
            method="POST",
            url=f"{self.BASE_URL}/customers",
            headers=self._auth_headers(),
            data=data,
        )

        return PaymentCustomer(
            customer_id=response["id"],
            email=response.get("email"),
            metadata=response.get("metadata", {}),
        )

    # -------------------------------------------------------------------------
    # 2. Create Payment Intent
    # -------------------------------------------------------------------------
    async def create_payment_intent(
        self,
        amount: int,
        currency: str,
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentIntent:

        data = {
            "amount": amount,
            "currency": currency.lower(),
            "automatic_payment_methods[enabled]": "true",
        }

        if customer_id:
            data["customer"] = customer_id

        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = str(v)

        response = await self._request(
            method="POST",
            url=f"{self.BASE_URL}/payment_intents",
            headers=self._auth_headers(),
            data=data,
        )

        return PaymentIntent(
            intent_id=response["id"],
            amount=response["amount"],
            currency=response["currency"],
            client_secret=response.get("client_secret"),
            status=response.get("status"),
            metadata=response.get("metadata", {}),
        )

    # -------------------------------------------------------------------------
    # 3. Refund Payment
    # -------------------------------------------------------------------------
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentRefund:

        data = {
            "payment_intent": transaction_id,
        }

        if amount:
            data["amount"] = amount

        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = str(v)

        response = await self._request(
            method="POST",
            url=f"{self.BASE_URL}/refunds",
            headers=self._auth_headers(),
            data=data,
        )

        return PaymentRefund(
            refund_id=response["id"],
            amount=response["amount"],
            currency=response["currency"],
            status=response["status"],
            metadata=response.get("metadata", {}),
        )

    # -------------------------------------------------------------------------
    # 4. Webhook Signature Verification
    # -------------------------------------------------------------------------
    async def verify_webhook_signature(self, payload: bytes, headers: Dict[str, str]) -> bool:
        """
        Stripe Webhook Verification:
        Stripe sends a header: `Stripe-Signature`
        Format:
            t=timestamp, v1=signature_hash
        """

        if not self.webhook_secret:
            raise RuntimeError("Stripe webhook secret not configured.")

        sig_header = headers.get("stripe-signature")
        if not sig_header:
            return False

        # Parse Stripe-Signature header
        try:
            values = dict(
                part.split("=", 1) for part in sig_header.split(",")
            )
            timestamp = values.get("t")
            signature = values.get("v1")
        except Exception:
            return False

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode()

        expected_signature = hmac.new(
            key=self.webhook_secret.encode(),
            msg=signed_payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        # Timing-safe comparison
        return hmac.compare_digest(signature, expected_signature)

    # -------------------------------------------------------------------------
    # 5. Parse Webhook Event
    # -------------------------------------------------------------------------
    async def parse_webhook_event(self, payload: bytes) -> Dict[str, Any]:
        return self._json(payload)

    # -------------------------------------------------------------------------
    # 6. Get Transaction Status
    # -------------------------------------------------------------------------
    async def get_transaction_status(self, transaction_id: str) -> PaymentTransactionStatus:

        response = await self._request(
            method="GET",
            url=f"{self.BASE_URL}/payment_intents/{transaction_id}",
            headers=self._auth_headers(),
        )

        return PaymentTransactionStatus(
            transaction_id=response["id"],
            status=response.get("status"),
            raw=response,
        )

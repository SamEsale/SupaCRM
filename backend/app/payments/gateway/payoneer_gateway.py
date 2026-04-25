from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

from backend.app.payments.gateway.base_gateway import (
    BasePaymentGateway,
    PaymentAuthorizationResult,
    PaymentCaptureResult,
    PaymentRefundResult,
)
from backend.app.payments.exceptions import (
    PaymentAuthorizationError,
    PaymentCaptureError,
    PaymentRefundError,
)
from backend.app.core.config import settings


class PayoneerGateway(BasePaymentGateway):
    """
    Payoneer gateway implementation using OAuth2-based access tokens
    and the standard Payoneer Checkout API.

    This class maintains strict alignment with the BasePaymentGateway
    abstraction and produces typed result objects used by the service layer.
    """

    BASE_URL = "https://api.payoneer.com/v4"  # Production endpoint
    TIMEOUT = 20

    def __init__(self) -> None:
        # Configuration from .env or settings manager
        self.client_id = settings.PAYONEER_CLIENT_ID
        self.client_secret = settings.PAYONEER_CLIENT_SECRET
        self.program_id = settings.PAYONEER_PROGRAM_ID
        self._cached_access_token: Optional[str] = None

    # -------------------------------------------------------------------------
    # INTERNAL AUTHENTICATION
    # -------------------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """
        Retrieves and caches the OAuth2 access token required for all Payoneer API calls.
        Automatically refreshes on expiration (in a complete implementation).
        """

        # Reuse cached token if available
        if self._cached_access_token:
            return self._cached_access_token

        token_url = f"{self.BASE_URL}/oauth2/token"

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
            except Exception as exc:
                raise PaymentAuthorizationError(
                    gateway="payoneer",
                    message="Failed to retrieve Payoneer access token.",
                    details={"exception": str(exc)},
                ) from exc

        if response.status_code != 200:
            raise PaymentAuthorizationError(
                gateway="payoneer",
                message="Payoneer token request failed.",
                details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()
        self._cached_access_token = data.get("access_token")
        return self._cached_access_token

    async def _client(self) -> httpx.AsyncClient:
        """
        Creates an httpx client with authorization headers attached.
        """
        token = await self._get_access_token()

        return httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.TIMEOUT,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    # -------------------------------------------------------------------------
    # PUBLIC GATEWAY OPERATIONS
    # -------------------------------------------------------------------------

    async def authorize_payment(
        self,
        amount: int,
        currency: str,
        customer_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentAuthorizationResult:
        """
        Creates a Payoneer Checkout session (authorization). Payoneer's API uses
        two-step payment flows: 
        1) create checkout → get consumer redirect URL
        2) capture/charge later.
        """

        payload = {
            "program_id": self.program_id,
            "amount": {
                "value": amount,
                "currency": currency,
            },
            "description": description or "Payment Authorization",
            "redirect_urls": {
                "success_url": settings.PAYMENTS_SUCCESS_URL,
                "failure_url": settings.PAYMENTS_FAILURE_URL,
            },
            "metadata": metadata or {},
        }

        client = await self._client()

        try:
            response = await client.post("/checkout", json=payload)
        except Exception as exc:
            raise PaymentAuthorizationError(
                gateway="payoneer",
                message="Payoneer authorization request failed.",
                details={"exception": str(exc)},
            ) from exc
        finally:
            await client.aclose()

        if response.status_code not in (200, 201):
            raise PaymentAuthorizationError(
                gateway="payoneer",
                message="Payoneer returned an unsuccessful authorization response.",
                details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()

        return PaymentAuthorizationResult(
            gateway="payoneer",
            payment_intent_id=data["checkout_id"],
            client_secret=None,  # Payoneer does not use client secrets
            redirect_url=data.get("redirect_url"),
            raw=data,
        )

    # -------------------------------------------------------------------------

    async def capture_payment(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
    ) -> PaymentCaptureResult:
        """
        Captures a previously authorized Payoneer checkout transaction.
        """

        payload = {}
        if amount:
            payload["amount"] = {"value": amount}

        client = await self._client()

        try:
            response = await client.post(
                f"/checkout/{payment_intent_id}/capture",
                json=payload,
            )
        except Exception as exc:
            raise PaymentCaptureError(
                gateway="payoneer",
                message="Payoneer capture request failed.",
                details={"exception": str(exc)},
            ) from exc
        finally:
            await client.aclose()

        if response.status_code not in (200, 201):
            raise PaymentCaptureError(
                gateway="payoneer",
                message="Capture unsuccessful.",
                details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()

        return PaymentCaptureResult(
            gateway="payoneer",
            transaction_id=data.get("transaction_id"),
            raw=data,
        )

    # -------------------------------------------------------------------------

    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> PaymentRefundResult:
        """
        Issues a partial or full refund for a Payoneer transaction.
        """

        payload = {}
        if amount:
            payload["amount"] = {"value": amount}
        if reason:
            payload["reason"] = reason

        client = await self._client()

        try:
            response = await client.post(
                f"/transactions/{transaction_id}/refund",
                json=payload,
            )
        except Exception as exc:
            raise PaymentRefundError(
                gateway="payoneer",
                message="Payoneer refund request failed.",
                details={"exception": str(exc)},
            ) from exc
        finally:
            await client.aclose()

        if response.status_code not in (200, 201):
            raise PaymentRefundError(
                gateway="payoneer",
                message="Refund unsuccessful.",
                details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()

        return PaymentRefundResult(
            gateway="payoneer",
            refund_id=data.get("refund_id"),
            raw=data,
        )

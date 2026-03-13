# backend/app/payments/gateway/base_gateway.py
"""
Abstract base gateway for all payment providers (Stripe, Payoneer, Revolut).
This file provides:
 - typed request/response models (Pydantic)
 - an async HTTP wrapper using httpx
 - an abstract interface (async) that concrete gateways must implement

Target: Python 3.11+, httpx.AsyncClient, Pydantic v2, async-first design.
"""

from __future__ import annotations

import abc
import json
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, Field


# -------------------------
# Shared data models
# -------------------------
class PaymentInitRequest(BaseModel):
    tenant_id: str
    customer_id: Optional[str] = None
    amount: Decimal
    currency: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PaymentResult(BaseModel):
    success: bool
    provider: str
    reference_id: Optional[str] = None
    status: str
    client_secret: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class RefundRequest(BaseModel):
    tenant_id: str
    payment_reference_id: str
    amount: Optional[Decimal] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RefundResult(BaseModel):
    success: bool
    provider: str
    refund_reference_id: Optional[str] = None
    status: str
    raw_response: Optional[Dict[str, Any]] = None


# -------------------------
# Base abstract gateway
# -------------------------
class BasePaymentGateway(abc.ABC):
    """
    Abstract base class defining the interface all payment gateways must follow.

    Concrete implementations MUST implement:
      - create_customer
      - initialize_payment
      - verify_payment
      - refund_payment
      - verify_webhook_signature
      - parse_webhook_event
      - get_transaction_status

    The class also exposes a shared async HTTP helper `_request`.
    """

    def __init__(self, provider_name: str, api_key: str = "", webhook_secret: Optional[str] = None):
        self.provider_name = provider_name
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        # one shared httpx client instance per gateway instance
        self._http: Optional[httpx.AsyncClient] = None

    # -------------------------
    # lifecycle for httpx client
    # -------------------------
    @property
    def http(self) -> httpx.AsyncClient:
        # lazy create client so we can safely import module-level without network ops
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=15.0)
        return self._http

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    # -------------------------
    # abstract interface
    # -------------------------
    @abc.abstractmethod
    async def create_customer(self, email: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create or fetch a customer in the payment provider.
        Return provider-specific customer payload (must include an id field).
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def initialize_payment(self, req: PaymentInitRequest) -> PaymentResult:
        """
        Initialize a payment intent or checkout session. Return PaymentResult.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def verify_payment(self, payment_reference_id: str) -> PaymentResult:
        """
        Verify the state of a payment/intent by provider reference id.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def refund_payment(self, req: RefundRequest) -> RefundResult:
        """
        Issue a refund through the payment provider.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def verify_webhook_signature(self, payload: bytes, headers: Dict[str, str]) -> bool:
        """
        Verify signature authenticity of incoming webhook.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def parse_webhook_event(self, payload: bytes) -> Dict[str, Any]:
        """
        Parse webhook payload and return normalized event dict.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Return provider transaction status info as dictionary.
        """
        raise NotImplementedError

    # -------------------------
    # shared http helper
    # -------------------------
    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Standardized HTTP wrapper that concrete gateways should use for outbound calls.
        Raises RuntimeError on HTTP errors so callers can catch and wrap appropriately.
        """
        _headers = {} if headers is None else dict(headers)
        # attach basic auth header if api_key provided and no Authorization header set
        if self.api_key and "Authorization" not in _headers:
            _headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = await self.http.request(
                method=method.upper(),
                url=url,
                headers=_headers,
                params=params,
                data=data,
                json=json_payload,
                timeout=timeout or 15.0,
            )

            # raise for non-2xx responses to unify error handling
            resp.raise_for_status()

            # Try to parse JSON; if not JSON, return raw text in a dict
            try:
                return resp.json()
            except Exception:
                return {"raw_text": resp.text}

        except httpx.HTTPStatusError as exc:
            # include response body to help debugging
            body = exc.response.text if exc.response is not None else "<no body>"
            raise RuntimeError(f"Payment gateway HTTP error: {exc.response.status_code} - {body}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Payment gateway request failure: {str(exc)}") from exc
        except Exception as exc:
            raise RuntimeError(f"Unexpected payment gateway error: {str(exc)}") from exc

    # -------------------------
    # small helper to parse json bytes
    # -------------------------
    @staticmethod
    def _parse_json_bytes(payload: bytes) -> Dict[str, Any]:
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Invalid JSON payload") from exc

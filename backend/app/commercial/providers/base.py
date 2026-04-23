from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class CommercialProviderSubscriptionResult:
    provider: str
    provider_customer_id: str | None
    provider_subscription_id: str | None
    status: str
    trial_end_at: datetime | None
    current_period_start_at: datetime | None
    current_period_end_at: datetime | None
    cancel_at_period_end: bool
    raw: dict[str, Any]


@dataclass(slots=True)
class CommercialWebhookEvent:
    provider: str
    event_id: str
    event_type: str
    raw_payload: dict[str, Any]
    customer_id: str | None = None
    subscription_id: str | None = None


@dataclass(slots=True)
class CommercialCheckoutSessionResult:
    provider: str
    session_id: str
    url: str
    mode: str
    provider_customer_id: str | None
    provider_subscription_id: str | None
    raw: dict[str, Any]


class CommercialProvider(abc.ABC):
    @abc.abstractmethod
    async def create_customer(
        self,
        *,
        email: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def create_subscription(
        self,
        *,
        customer_id: str,
        price_id: str,
        metadata: dict[str, Any] | None = None,
        trial_days: int = 0,
    ) -> CommercialProviderSubscriptionResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def cancel_subscription(
        self,
        *,
        subscription_id: str,
        cancel_at_period_end: bool = False,
    ) -> CommercialProviderSubscriptionResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def verify_webhook_signature(self, *, payload: bytes, headers: dict[str, str]) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def parse_webhook_event(self, *, payload: bytes) -> CommercialWebhookEvent:
        raise NotImplementedError

    async def get_payment_method(
        self,
        *,
        payment_method_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def attach_payment_method(
        self,
        *,
        customer_id: str,
        payment_method_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def detach_payment_method(
        self,
        *,
        payment_method_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def list_payment_methods(
        self,
        *,
        customer_id: str,
        type: str = "card",
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def set_default_payment_method(
        self,
        *,
        customer_id: str,
        payment_method_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

    async def get_setup_intent(
        self,
        *,
        setup_intent_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

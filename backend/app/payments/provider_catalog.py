from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_GATEWAY_PROVIDERS: tuple[str, ...] = (
    "stripe",
    "revolut_business",
    "payoneer",
)

SUPPORTED_GATEWAY_MODES: tuple[str, ...] = ("test", "live")

PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "stripe": "Stripe",
    "revolut_business": "Revolut Business",
    "payoneer": "Payoneer",
}

PROVIDER_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "stripe": ("publishable_key", "secret_key", "webhook_secret"),
    "revolut_business": ("merchant_id", "api_key", "webhook_secret"),
    "payoneer": ("account_id", "client_id", "client_secret", "webhook_secret"),
}


@dataclass(frozen=True, slots=True)
class PaymentProviderCapability:
    provider: str
    display_name: str
    supports_checkout_payments: bool
    supports_webhooks: bool
    supports_automated_subscriptions: bool
    operator_summary: str


PROVIDER_CAPABILITIES: dict[str, PaymentProviderCapability] = {
    "stripe": PaymentProviderCapability(
        provider="stripe",
        display_name="Stripe",
        supports_checkout_payments=True,
        supports_webhooks=True,
        supports_automated_subscriptions=True,
        operator_summary=(
            "Tenant-scoped Stripe credentials can power checkout foundations, "
            "webhooks, and commercial subscription automation."
        ),
    ),
    "revolut_business": PaymentProviderCapability(
        provider="revolut_business",
        display_name="Revolut Business",
        supports_checkout_payments=False,
        supports_webhooks=False,
        supports_automated_subscriptions=False,
        operator_summary=(
            "Revolut Business settings are stored for operator readiness, but "
            "automated subscription billing is not implemented in this slice."
        ),
    ),
    "payoneer": PaymentProviderCapability(
        provider="payoneer",
        display_name="Payoneer",
        supports_checkout_payments=False,
        supports_webhooks=False,
        supports_automated_subscriptions=False,
        operator_summary=(
            "Payoneer settings are stored for operator readiness, but automated "
            "subscription billing is not implemented in this slice."
        ),
    ),
}


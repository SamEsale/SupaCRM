from typing import Any

from app.commercial.providers.base import CommercialProvider, CommercialProviderSubscriptionResult, CommercialWebhookEvent
from app.commercial.providers.stripe import StripeCommercialProvider
from app.payments.provider_catalog import PROVIDER_CAPABILITIES


def get_commercial_provider(
    provider: str,
    *,
    config: dict[str, Any] | None = None,
) -> CommercialProvider:
    normalized = provider.strip().lower()
    if normalized == "stripe":
        provider_config = config or {}
        return StripeCommercialProvider(
            api_key=provider_config.get("secret_key") or provider_config.get("api_key"),
            webhook_secret=provider_config.get("webhook_secret"),
        )
    capability = PROVIDER_CAPABILITIES.get(normalized)
    if capability and not capability.supports_automated_subscriptions:
        raise ValueError(
            f"Commercial subscription automation is not implemented for provider: {provider}"
        )
    raise ValueError(f"Unsupported commercial provider: {provider}")

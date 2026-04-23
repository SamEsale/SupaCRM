from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.payments.provider_catalog import (
    PROVIDER_CAPABILITIES,
    PROVIDER_DISPLAY_NAMES,
    PROVIDER_REQUIRED_FIELDS,
    SUPPORTED_GATEWAY_MODES,
    SUPPORTED_GATEWAY_PROVIDERS,
)


@dataclass(slots=True)
class PaymentGatewayProviderSettings:
    provider: str
    display_name: str
    is_enabled: bool
    is_default: bool
    mode: str
    account_id: str | None
    merchant_id: str | None
    publishable_key: str | None
    client_id: str | None
    secret_key_set: bool
    api_key_set: bool
    client_secret_set: bool
    webhook_secret_set: bool
    configuration_state: str
    validation_errors: list[str]
    updated_at: datetime | None


@dataclass(slots=True)
class PaymentGatewaySettingsSnapshot:
    default_provider: str | None
    providers: list[PaymentGatewayProviderSettings]
    updated_at: datetime | None


@dataclass(slots=True)
class PaymentGatewayProviderRecord:
    provider: str
    display_name: str
    is_enabled: bool
    is_default: bool
    mode: str
    account_id: str | None
    merchant_id: str | None
    publishable_key: str | None
    client_id: str | None
    secret_key: str | None
    api_key: str | None
    client_secret: str | None
    webhook_secret: str | None
    configuration_state: str
    validation_errors: list[str]
    updated_at: datetime | None


@dataclass(slots=True)
class PaymentProviderFoundation:
    provider: str
    display_name: str
    is_enabled: bool
    is_default: bool
    mode: str
    configuration_state: str
    foundation_state: str
    supports_checkout_payments: bool
    supports_webhooks: bool
    supports_automated_subscriptions: bool
    operator_summary: str
    validation_errors: list[str]
    updated_at: datetime | None


@dataclass(slots=True)
class PaymentProviderFoundationSnapshot:
    default_provider: str | None
    providers: list[PaymentProviderFoundation]
    updated_at: datetime | None


def _load_json(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _dump_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_GATEWAY_PROVIDERS:
        raise ValueError(
            "Unsupported payment provider. Allowed values: "
            + ", ".join(SUPPORTED_GATEWAY_PROVIDERS)
        )
    return normalized


def _normalize_mode(mode: str | None) -> str:
    if mode is None:
        return "test"
    normalized = mode.strip().lower()
    if normalized not in SUPPORTED_GATEWAY_MODES:
        raise ValueError(
            "Unsupported payment gateway mode. Allowed values: "
            + ", ".join(SUPPORTED_GATEWAY_MODES)
        )
    return normalized


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _provider_state(
    provider: str,
    *,
    payload: dict[str, object],
) -> tuple[str, list[str]]:
    required = PROVIDER_REQUIRED_FIELDS[provider]
    missing: list[str] = []

    for field in required:
        value = payload.get(field)
        if isinstance(value, str):
            present = bool(value.strip())
        else:
            present = value is not None
        if not present:
            missing.append(field)

    if len(missing) == len(required):
        return "not_configured", []
    if missing:
        return "incomplete", [f"Missing required field: {field}" for field in missing]
    return "configured", []


def _provider_from_payload(
    provider: str,
    *,
    payload: dict[str, object],
    default_provider: str | None,
) -> PaymentGatewayProviderSettings:
    state, validation_errors = _provider_state(provider, payload=payload)

    return PaymentGatewayProviderSettings(
        provider=provider,
        display_name=PROVIDER_DISPLAY_NAMES[provider],
        is_enabled=bool(payload.get("is_enabled", False)),
        is_default=default_provider == provider,
        mode=_normalize_mode(payload.get("mode") if isinstance(payload.get("mode"), str) else None),
        account_id=payload.get("account_id") if isinstance(payload.get("account_id"), str) else None,
        merchant_id=payload.get("merchant_id") if isinstance(payload.get("merchant_id"), str) else None,
        publishable_key=payload.get("publishable_key") if isinstance(payload.get("publishable_key"), str) else None,
        client_id=payload.get("client_id") if isinstance(payload.get("client_id"), str) else None,
        secret_key_set=bool(_clean_optional(payload.get("secret_key") if isinstance(payload.get("secret_key"), str) else None)),
        api_key_set=bool(_clean_optional(payload.get("api_key") if isinstance(payload.get("api_key"), str) else None)),
        client_secret_set=bool(_clean_optional(payload.get("client_secret") if isinstance(payload.get("client_secret"), str) else None)),
        webhook_secret_set=bool(_clean_optional(payload.get("webhook_secret") if isinstance(payload.get("webhook_secret"), str) else None)),
        configuration_state=state,
        validation_errors=validation_errors,
        updated_at=_parse_datetime(payload.get("updated_at")),
    )


def _provider_record_from_payload(
    provider: str,
    *,
    payload: dict[str, object],
    default_provider: str | None,
) -> PaymentGatewayProviderRecord:
    settings = _provider_from_payload(provider, payload=payload, default_provider=default_provider)
    return PaymentGatewayProviderRecord(
        provider=settings.provider,
        display_name=settings.display_name,
        is_enabled=settings.is_enabled,
        is_default=settings.is_default,
        mode=settings.mode,
        account_id=settings.account_id,
        merchant_id=settings.merchant_id,
        publishable_key=settings.publishable_key,
        client_id=settings.client_id,
        secret_key=_clean_optional(payload.get("secret_key") if isinstance(payload.get("secret_key"), str) else None),
        api_key=_clean_optional(payload.get("api_key") if isinstance(payload.get("api_key"), str) else None),
        client_secret=_clean_optional(payload.get("client_secret") if isinstance(payload.get("client_secret"), str) else None),
        webhook_secret=_clean_optional(payload.get("webhook_secret") if isinstance(payload.get("webhook_secret"), str) else None),
        configuration_state=settings.configuration_state,
        validation_errors=list(settings.validation_errors),
        updated_at=settings.updated_at,
    )


def _foundation_state(record: PaymentGatewayProviderRecord) -> str:
    capability = PROVIDER_CAPABILITIES[record.provider]
    if not record.is_enabled:
        return "disabled"
    if record.configuration_state != "configured":
        return "needs_configuration"
    if capability.supports_automated_subscriptions:
        return "ready"
    return "manual_only"


def _foundation_summary(record: PaymentGatewayProviderRecord) -> str:
    capability = PROVIDER_CAPABILITIES[record.provider]
    state = _foundation_state(record)
    if state == "disabled":
        return (
            f"{capability.display_name} is saved as an operator option, but it is currently disabled "
            "for this tenant."
        )
    if state == "needs_configuration":
        return (
            f"{capability.display_name} is not fully configured yet. Save the required tenant-scoped "
            "credentials before using it for billing operations."
        )
    if state == "ready":
        return capability.operator_summary
    return (
        f"{capability.display_name} is configured for operator visibility and manual readiness, "
        "but automated subscription billing is intentionally not implemented here."
    )


def _foundation_from_record(record: PaymentGatewayProviderRecord) -> PaymentProviderFoundation:
    capability = PROVIDER_CAPABILITIES[record.provider]
    return PaymentProviderFoundation(
        provider=record.provider,
        display_name=record.display_name,
        is_enabled=record.is_enabled,
        is_default=record.is_default,
        mode=record.mode,
        configuration_state=record.configuration_state,
        foundation_state=_foundation_state(record),
        supports_checkout_payments=capability.supports_checkout_payments,
        supports_webhooks=capability.supports_webhooks,
        supports_automated_subscriptions=capability.supports_automated_subscriptions,
        operator_summary=_foundation_summary(record),
        validation_errors=list(record.validation_errors),
        updated_at=record.updated_at,
    )


async def _tenant_column_exists(session: AsyncSession, column_name: str) -> bool:
    result = await session.execute(
        text(
            """
            select exists (
                select 1
                from information_schema.columns
                where table_schema = 'public'
                  and table_name = 'tenants'
                  and column_name = :column_name
            ) as column_exists
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


async def _get_gateway_settings_payload(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> tuple[dict[str, object], datetime | None]:
    result = await session.execute(
        text(
            """
            select payment_gateway_settings, updated_at
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Tenant not found")
    return _load_json(row.get("payment_gateway_settings")), row.get("updated_at")


async def get_payment_gateway_settings(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> PaymentGatewaySettingsSnapshot:
    if not await _tenant_column_exists(session, "payment_gateway_settings"):
        return PaymentGatewaySettingsSnapshot(
            default_provider=None,
            providers=[
                _provider_from_payload(provider, payload={}, default_provider=None)
                for provider in SUPPORTED_GATEWAY_PROVIDERS
            ],
            updated_at=None,
        )

    payload, updated_at = await _get_gateway_settings_payload(session, tenant_id=tenant_id)
    providers_payload = _load_json(payload.get("providers"))
    default_provider = payload.get("default_provider")
    normalized_default_provider = (
        str(default_provider) if isinstance(default_provider, str) and default_provider in SUPPORTED_GATEWAY_PROVIDERS else None
    )

    return PaymentGatewaySettingsSnapshot(
        default_provider=normalized_default_provider,
        providers=[
            _provider_from_payload(
                provider,
                payload=_load_json(providers_payload.get(provider)),
                default_provider=normalized_default_provider,
            )
            for provider in SUPPORTED_GATEWAY_PROVIDERS
        ],
        updated_at=_parse_datetime(payload.get("updated_at")) or updated_at,
    )


async def get_payment_gateway_provider_record(
    session: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
) -> PaymentGatewayProviderRecord:
    normalized_provider = _normalize_provider(provider)

    if not await _tenant_column_exists(session, "payment_gateway_settings"):
        raise ValueError(
            "Payment gateway settings require the latest database migration. Run alembic upgrade head and retry."
        )

    payload, _ = await _get_gateway_settings_payload(session, tenant_id=tenant_id)
    providers_payload = _load_json(payload.get("providers"))
    default_provider = payload.get("default_provider")
    normalized_default_provider = (
        str(default_provider)
        if isinstance(default_provider, str) and default_provider in SUPPORTED_GATEWAY_PROVIDERS
        else None
    )

    return _provider_record_from_payload(
        normalized_provider,
        payload=_load_json(providers_payload.get(normalized_provider)),
        default_provider=normalized_default_provider,
    )


async def get_payment_provider_foundation(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> PaymentProviderFoundationSnapshot:
    if not await _tenant_column_exists(session, "payment_gateway_settings"):
        settings = await get_payment_gateway_settings(session, tenant_id=tenant_id)
        return PaymentProviderFoundationSnapshot(
            default_provider=settings.default_provider,
            providers=[
                _foundation_from_record(
                    _provider_record_from_payload(
                        provider.provider,
                        payload={},
                        default_provider=settings.default_provider,
                    )
                )
                for provider in settings.providers
            ],
            updated_at=settings.updated_at,
        )

    payload, updated_at = await _get_gateway_settings_payload(session, tenant_id=tenant_id)
    providers_payload = _load_json(payload.get("providers"))
    default_provider = payload.get("default_provider")
    normalized_default_provider = (
        str(default_provider)
        if isinstance(default_provider, str) and default_provider in SUPPORTED_GATEWAY_PROVIDERS
        else None
    )
    records = [
        _provider_record_from_payload(
            provider,
            payload=_load_json(providers_payload.get(provider)),
            default_provider=normalized_default_provider,
        )
        for provider in SUPPORTED_GATEWAY_PROVIDERS
    ]
    return PaymentProviderFoundationSnapshot(
        default_provider=normalized_default_provider,
        providers=[_foundation_from_record(record) for record in records],
        updated_at=_parse_datetime(payload.get("updated_at")) or updated_at,
    )


async def update_payment_gateway_provider(
    session: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    is_enabled: bool,
    is_default: bool,
    mode: str | None,
    account_id: str | None = None,
    merchant_id: str | None = None,
    publishable_key: str | None = None,
    client_id: str | None = None,
    secret_key: str | None = None,
    api_key: str | None = None,
    client_secret: str | None = None,
    webhook_secret: str | None = None,
) -> PaymentGatewaySettingsSnapshot:
    normalized_provider = _normalize_provider(provider)

    if not await _tenant_column_exists(session, "payment_gateway_settings"):
        raise ValueError(
            "Payment gateway settings require the latest database migration. Run alembic upgrade head and retry."
        )

    current_payload, _ = await _get_gateway_settings_payload(session, tenant_id=tenant_id)
    providers_payload = _load_json(current_payload.get("providers"))
    existing_provider_payload = _load_json(providers_payload.get(normalized_provider))

    next_provider_payload: dict[str, object] = {
        **existing_provider_payload,
        "is_enabled": is_enabled,
        "mode": _normalize_mode(mode),
        "account_id": _clean_optional(account_id),
        "merchant_id": _clean_optional(merchant_id),
        "publishable_key": _clean_optional(publishable_key),
        "client_id": _clean_optional(client_id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if _clean_optional(secret_key):
        next_provider_payload["secret_key"] = _clean_optional(secret_key)
    if _clean_optional(api_key):
        next_provider_payload["api_key"] = _clean_optional(api_key)
    if _clean_optional(client_secret):
        next_provider_payload["client_secret"] = _clean_optional(client_secret)
    if _clean_optional(webhook_secret):
        next_provider_payload["webhook_secret"] = _clean_optional(webhook_secret)

    providers_payload[normalized_provider] = next_provider_payload
    next_state, _ = _provider_state(normalized_provider, payload=next_provider_payload)

    if is_default and (not is_enabled or next_state != "configured"):
        raise ValueError(
            "Default payment provider must be enabled and fully configured before it can be selected."
        )

    current_default_provider = current_payload.get("default_provider")
    default_provider = (
        normalized_provider
        if is_default
        else (
            None
            if current_default_provider == normalized_provider
            else current_default_provider if isinstance(current_default_provider, str) else None
        )
    )

    next_payload = {
        "default_provider": default_provider if default_provider in SUPPORTED_GATEWAY_PROVIDERS else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "providers": providers_payload,
    }

    await session.execute(
        text(
            """
            update public.tenants
            set payment_gateway_settings = cast(:payment_gateway_settings as jsonb),
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "payment_gateway_settings": _dump_json(next_payload),
        },
    )

    return await get_payment_gateway_settings(session, tenant_id=tenant_id)

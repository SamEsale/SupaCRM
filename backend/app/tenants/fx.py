from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation


@dataclass(slots=True)
class TenantCurrencyConversion:
    source_amount: Decimal
    source_currency: str
    converted_amount: Decimal
    converted_currency: str
    rate: Decimal
    rate_source: str
    rate_as_of: datetime


def _normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        return None
    return normalized


def _normalize_decimal(value: Decimal | str | int | float | None) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        normalized = value
    else:
        try:
            normalized = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    return normalized


def convert_tenant_secondary_currency_amount(
    *,
    amount: Decimal | str | int | float,
    amount_currency: str,
    default_currency: str | None,
    secondary_currency: str | None,
    secondary_currency_rate: Decimal | str | int | float | None,
    rate_source: str | None,
    rate_as_of: datetime | None,
) -> TenantCurrencyConversion | None:
    normalized_default_currency = _normalize_currency(default_currency)
    normalized_secondary_currency = _normalize_currency(secondary_currency)
    normalized_rate = _normalize_decimal(secondary_currency_rate)
    normalized_amount = _normalize_decimal(amount)
    normalized_amount_currency = _normalize_currency(amount_currency)

    if (
        normalized_default_currency is None
        or normalized_secondary_currency is None
        or normalized_default_currency == normalized_secondary_currency
        or normalized_rate is None
        or normalized_rate <= 0
        or normalized_amount is None
        or normalized_amount_currency is None
        or rate_source is None
        or rate_as_of is None
    ):
        return None

    if normalized_amount_currency == normalized_default_currency:
        converted_amount = (normalized_amount * normalized_rate).quantize(Decimal("0.01"))
        converted_currency = normalized_secondary_currency
    elif normalized_amount_currency == normalized_secondary_currency:
        converted_amount = (normalized_amount / normalized_rate).quantize(Decimal("0.01"))
        converted_currency = normalized_default_currency
    else:
        return None

    return TenantCurrencyConversion(
        source_amount=normalized_amount.quantize(Decimal("0.01")),
        source_currency=normalized_amount_currency,
        converted_amount=converted_amount,
        converted_currency=converted_currency,
        rate=normalized_rate.quantize(Decimal("0.000001")),
        rate_source=rate_source,
        rate_as_of=rate_as_of,
    )

# WhatsApp Business integration for Sales module
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


ALLOWED_MESSAGE_TYPES: tuple[str, ...] = (
    "text",
    "image",
    "document",
    "audio",
    "video",
    "unknown",
)

NEW_LEAD_STAGE = "new lead"
DEFAULT_LEAD_STATUS = "open"
SOURCE_CHANNEL = "whatsapp"


@dataclass(slots=True)
class WhatsAppLeadPayload:
    tenant_id: str
    whatsapp_account_id: str
    sender_phone: str
    sender_name: str | None
    message_text: str | None
    message_type: str
    received_at: datetime
    source_channel: str
    campaign: str | None
    metadata: dict[str, Any]
    raw_payload: dict[str, Any]


def _clean_required(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")

    return cleaned


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def _normalize_phone(value: str | None) -> str:
    phone = _clean_required(value, "sender_phone")

    normalized = phone.replace(" ", "").replace("-", "")
    if normalized.startswith("+"):
        candidate = normalized[1:]
        if not candidate.isdigit():
            raise ValueError("sender_phone must contain only digits and an optional leading +")
    elif not normalized.isdigit():
        raise ValueError("sender_phone must contain only digits and an optional leading +")

    return normalized


def _normalize_message_type(value: str | None) -> str:
    if value is None:
        return "unknown"

    normalized = value.strip().lower()
    if not normalized:
        return "unknown"

    if normalized not in ALLOWED_MESSAGE_TYPES:
        return "unknown"

    return normalized


def _parse_received_at(value: Any) -> datetime:
    if value is None:
        return datetime.now(UTC)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return datetime.now(UTC)

        if raw.isdigit():
            return datetime.fromtimestamp(int(raw), tz=UTC)

        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("received_at must be ISO-8601 or unix timestamp") from exc

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    raise ValueError("received_at must be ISO-8601 datetime, unix timestamp, or datetime object")


def _extract_string(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _extract_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if metadata is None:
        return {}

    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")

    return metadata


def parse_inbound_whatsapp_lead(
    payload: dict[str, Any],
    *,
    tenant_id: str,
) -> WhatsAppLeadPayload:
    """
    Normalize a placeholder inbound WhatsApp payload into an internal lead shape.

    Accepted placeholder field aliases:
    - whatsapp_account_id: whatsapp_account_id | business_account_id | account_id
    - sender_phone: sender_phone | phone | from
    - sender_name: sender_name | profile_name | name
    - message_text: message_text | text | body | message
    - message_type: message_type | type
    - received_at: received_at | timestamp
    - campaign: campaign

    This function intentionally does NOT call external providers.
    It prepares a normalized structure that later phases can map into CRM/Sales records.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    normalized_tenant_id = _clean_required(tenant_id, "tenant_id")
    whatsapp_account_id = _clean_required(
        _extract_string(payload, "whatsapp_account_id", "business_account_id", "account_id"),
        "whatsapp_account_id",
    )
    sender_phone = _normalize_phone(
        _extract_string(payload, "sender_phone", "phone", "from"),
    )
    sender_name = _clean_optional(
        _extract_string(payload, "sender_name", "profile_name", "name"),
    )
    message_text = _clean_optional(
        _extract_string(payload, "message_text", "text", "body", "message"),
    )
    message_type = _normalize_message_type(
        _extract_string(payload, "message_type", "type"),
    )
    received_at = _parse_received_at(payload.get("received_at", payload.get("timestamp")))
    campaign = _clean_optional(_extract_string(payload, "campaign"))
    metadata = _extract_metadata(payload)

    return WhatsAppLeadPayload(
        tenant_id=normalized_tenant_id,
        whatsapp_account_id=whatsapp_account_id,
        sender_phone=sender_phone,
        sender_name=sender_name,
        message_text=message_text,
        message_type=message_type,
        received_at=received_at,
        source_channel=SOURCE_CHANNEL,
        campaign=campaign,
        metadata=metadata,
        raw_payload=payload,
    )


def build_new_lead_contact_defaults(normalized: WhatsAppLeadPayload) -> dict[str, Any]:
    """
    Convert the normalized WhatsApp payload into a CRM-contact-ready placeholder structure.

    Later phases can pass this directly into CRM/contact creation logic.
    """
    notes_parts: list[str] = [
        "Lead source: WhatsApp Business",
        f"WhatsApp account: {normalized.whatsapp_account_id}",
        f"Message type: {normalized.message_type}",
        f"Received at: {normalized.received_at.isoformat()}",
    ]

    if normalized.message_text:
        notes_parts.append(f"Message: {normalized.message_text}")

    if normalized.campaign:
        notes_parts.append(f"Campaign: {normalized.campaign}")

    return {
        "first_name": normalized.sender_name or "WhatsApp Lead",
        "last_name": None,
        "email": None,
        "phone": normalized.sender_phone,
        "company": None,
        "job_title": None,
        "notes": "\n".join(notes_parts),
    }


def build_new_lead_deal_defaults(
    normalized: WhatsAppLeadPayload,
    *,
    company_id: str,
) -> dict[str, Any]:
    """
    Convert the normalized WhatsApp payload into a Sales-deal-ready placeholder structure.

    Since company_id is required by the current deal schema, the caller must provide one.
    Later phases may replace this with a dedicated lead entity or lead-company bootstrap flow.
    """
    normalized_company_id = _clean_required(company_id, "company_id")

    if normalized.sender_name:
        deal_name = f"WhatsApp Lead - {normalized.sender_name}"
    else:
        deal_name = f"WhatsApp Lead - {normalized.sender_phone}"

    notes_parts: list[str] = [
        "Created from inbound WhatsApp message.",
        f"WhatsApp account: {normalized.whatsapp_account_id}",
        f"Sender phone: {normalized.sender_phone}",
        f"Received at: {normalized.received_at.isoformat()}",
    ]

    if normalized.message_text:
        notes_parts.append(f"Initial message: {normalized.message_text}")

    if normalized.campaign:
        notes_parts.append(f"Campaign: {normalized.campaign}")

    return {
        "name": deal_name,
        "company_id": normalized_company_id,
        "contact_id": None,
        "product_id": None,
        "amount": 0,
        "currency": "USD",
        "stage": NEW_LEAD_STAGE,
        "status": DEFAULT_LEAD_STATUS,
        "expected_close_date": None,
        "notes": "\n".join(notes_parts),
    }
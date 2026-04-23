from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commercial.providers import get_commercial_provider
from app.commercial.providers.base import (
    CommercialProviderSubscriptionResult,
    CommercialWebhookEvent,
)
from app.core.config import settings
from app.core.security.auth_cache import auth_cache
from app.payments.provider_catalog import PROVIDER_DISPLAY_NAMES
from app.payments.settings_service import get_payment_gateway_provider_record


COMMERCIAL_STATES: tuple[str, ...] = (
    "pending",
    "trial",
    "active",
    "past_due",
    "grace",
    "suspended",
    "canceled",
)
DEFAULT_COMMERCIAL_PLAN_CODE = "starter"
DEFAULT_COMMERCIAL_PROVIDER = "stripe"
DEFAULT_TRIAL_DAYS = 14
DEFAULT_GRACE_DAYS = 7
DEFAULT_PLAN_FEATURES: dict[str, Any] = {
    "tier": "starter",
    "self_service": True,
    "included_capabilities": [
        "Multi-tenant authentication and RBAC",
        "CRM core for companies and contacts",
        "Sales, quotes, and invoices",
        "Product catalog with image validation",
        "Commercial subscriptions and onboarding",
        "Production deployment, observability, recovery, and security hardening",
        "Redis-backed auth/session caching and worker processing",
        "Stripe-backed billing lifecycle and webhooks",
    ],
    "launch_limitations": [
        "Marketing automation remains staged",
        "Social connectors remain staged",
        "Advanced accounting and reporting expansion remain staged",
        "External CDN/WAF policy remains staged",
    ],
}
DEFAULT_YEARLY_PLAN_CODE = "starter_yearly"
DEFAULT_YEARLY_PLAN_FEATURES: dict[str, Any] = {
    **DEFAULT_PLAN_FEATURES,
    "billing_motion": "yearly",
}
STRIPE_COMMERCIAL_ACTIVE_STATUSES: frozenset[str] = frozenset({"trialing", "trial", "active", "past_due"})
STRIPE_PENDING_STATUSES: frozenset[str] = frozenset({"incomplete", "incomplete_expired", "paused"})
DEFAULT_PLAN_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "code": DEFAULT_COMMERCIAL_PLAN_CODE,
        "name": "Starter",
        "description": "Starter SaaS plan billed monthly",
        "provider": DEFAULT_COMMERCIAL_PROVIDER,
        "provider_price_id": None,
        "billing_interval": "month",
        "price_amount": Decimal("0.00"),
        "currency": "USD",
        "trial_days": DEFAULT_TRIAL_DAYS,
        "grace_days": DEFAULT_GRACE_DAYS,
        "is_active": True,
        "features": DEFAULT_PLAN_FEATURES,
    },
    {
        "code": DEFAULT_YEARLY_PLAN_CODE,
        "name": "Starter Yearly",
        "description": "Starter SaaS plan billed yearly",
        "provider": DEFAULT_COMMERCIAL_PROVIDER,
        "provider_price_id": None,
        "billing_interval": "year",
        "price_amount": Decimal("0.00"),
        "currency": "USD",
        "trial_days": DEFAULT_TRIAL_DAYS,
        "grace_days": DEFAULT_GRACE_DAYS,
        "is_active": True,
        "features": DEFAULT_YEARLY_PLAN_FEATURES,
    },
)


@dataclass(slots=True)
class CommercialPlanDetails:
    id: str
    code: str
    name: str
    description: str | None
    provider: str
    provider_price_id: str | None
    billing_interval: str
    price_amount: Decimal
    currency: str
    trial_days: int
    grace_days: int
    is_active: bool
    features: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class CommercialSubscriptionDetails:
    id: str
    tenant_id: str
    plan_id: str
    plan_code: str
    plan_name: str
    provider: str
    provider_customer_id: str | None
    provider_subscription_id: str | None
    subscription_status: str | None
    commercial_state: str
    state_reason: str | None
    trial_start_at: datetime | None
    trial_end_at: datetime | None
    current_period_start_at: datetime | None
    current_period_end_at: datetime | None
    grace_end_at: datetime | None
    cancel_at_period_end: bool
    activated_at: datetime | None
    reactivated_at: datetime | None
    suspended_at: datetime | None
    canceled_at: datetime | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class CommercialBillingCycleDetails:
    id: str
    tenant_id: str
    subscription_id: str
    cycle_number: int
    period_start_at: datetime
    period_end_at: datetime
    due_at: datetime
    amount: Decimal
    currency: str
    status: str
    invoice_id: str | None
    provider_event_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class CommercialBillingEventDetails:
    id: str
    tenant_id: str | None
    subscription_id: str | None
    provider: str
    external_event_id: str
    event_type: str
    processing_status: str
    action_taken: str | None
    error_message: str | None
    raw_payload: dict[str, Any]
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class CommercialSubscriptionSummary:
    subscription: CommercialSubscriptionDetails | None
    recent_billing_cycles: list[CommercialBillingCycleDetails]
    recent_billing_events: list[CommercialBillingEventDetails]


@dataclass(slots=True)
class TenantCommercialStatus:
    current_plan: CommercialPlanDetails | None
    subscription: CommercialSubscriptionDetails | None
    subscription_status: str | None
    trial_status: str
    next_billing_at: datetime | None
    renewal_at: datetime | None
    provider: str | None
    provider_name: str | None
    provider_customer_id: str | None
    provider_subscription_id: str | None
    commercially_active: bool


@dataclass(slots=True)
class CommercialCheckoutSessionDetails:
    provider: str
    session_id: str
    url: str
    mode: str
    provider_customer_id: str | None
    provider_subscription_id: str | None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _commercial_state_to_tenant_status(commercial_state: str) -> tuple[str, bool]:
    normalized = commercial_state.strip().lower()
    if normalized == "pending":
        return "suspended", False
    if normalized in {"trial", "active", "past_due", "grace"}:
        return "active", True
    if normalized == "suspended":
        return "suspended", False
    if normalized == "canceled":
        return "disabled", False
    raise ValueError(f"Unsupported commercial state: {commercial_state}")


def _normalize_subscription_status(subscription_status: str | None) -> str | None:
    if subscription_status is None:
        return None
    normalized = subscription_status.strip().lower()
    return normalized or None


def _map_provider_status(provider_status: str) -> str:
    status = provider_status.lower()
    if status in {"trialing", "trial"}:
        return "trial"
    if status == "active":
        return "active"
    if status in {"past_due", "past-due", "unpaid"}:
        return "past_due"
    if status == "grace":
        return "grace"
    if status in {"canceled", "cancelled", "incomplete_expired"}:
        return "canceled"
    if status in {"paused", "suspended"}:
        return "suspended"
    if status in STRIPE_PENDING_STATUSES:
        return "pending"
    return "pending"


def derive_commercial_state(
    *,
    provider: str | None,
    subscription_status: str | None,
    commercial_state: str | None = None,
) -> str:
    normalized_provider = (provider or "").strip().lower()
    normalized_status = _normalize_subscription_status(subscription_status)
    if normalized_provider == "stripe" and normalized_status:
        return _map_provider_status(normalized_status)
    if commercial_state:
        return _normalize_state(commercial_state)
    return "pending"


def is_commercially_active(
    subscription_status: str | None,
    *,
    provider: str | None = None,
    commercial_state: str | None = None,
) -> bool:
    normalized_provider = (provider or "").strip().lower()
    normalized_status = _normalize_subscription_status(subscription_status)
    if normalized_provider == "stripe":
        return normalized_status in STRIPE_COMMERCIAL_ACTIVE_STATUSES
    if not commercial_state:
        return False
    return commercial_state.strip().lower() in {"trial", "active", "past_due", "grace"}


def summarize_plan_features(features: dict[str, Any] | None) -> list[str]:
    if not isinstance(features, dict):
        return []

    included = features.get("included_capabilities")
    if isinstance(included, list):
        summary = [str(item).strip() for item in included if str(item).strip()]
        if summary:
            return summary[:5]

    limitations = features.get("launch_limitations")
    if isinstance(limitations, list):
        summary = [str(item).strip() for item in limitations if str(item).strip()]
        if summary:
            return summary[:5]

    tier = features.get("tier")
    if isinstance(tier, str) and tier.strip():
        return [f"{tier.strip().title()} tier"]

    return []


def _normalize_state(commercial_state: str) -> str:
    normalized = commercial_state.strip().lower()
    if normalized not in COMMERCIAL_STATES:
        raise ValueError(f"Unsupported commercial state: {commercial_state}")
    return normalized


def _row_to_plan(row: dict[str, Any]) -> CommercialPlanDetails:
    return CommercialPlanDetails(
        id=str(row["id"]),
        code=str(row["code"]),
        name=str(row["name"]),
        description=row["description"],
        provider=str(row["provider"]),
        provider_price_id=row["provider_price_id"],
        billing_interval=str(row["billing_interval"]),
        price_amount=Decimal(str(row["price_amount"])),
        currency=str(row["currency"]),
        trial_days=int(row["trial_days"]),
        grace_days=int(row["grace_days"]),
        is_active=bool(row["is_active"]),
        features=dict(row["features"] or {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_subscription(row: dict[str, Any]) -> CommercialSubscriptionDetails:
    return CommercialSubscriptionDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        plan_id=str(row["plan_id"]),
        plan_code=str(row["plan_code"]),
        plan_name=str(row["plan_name"]),
        provider=str(row["provider"]),
        provider_customer_id=row["provider_customer_id"],
        provider_subscription_id=row["provider_subscription_id"],
        subscription_status=row.get("subscription_status"),
        commercial_state=str(row["commercial_state"]),
        state_reason=row["state_reason"],
        trial_start_at=row["trial_start_at"],
        trial_end_at=row["trial_end_at"],
        current_period_start_at=row["current_period_start_at"],
        current_period_end_at=row["current_period_end_at"],
        grace_end_at=row["grace_end_at"],
        cancel_at_period_end=bool(row["cancel_at_period_end"]),
        activated_at=row["activated_at"],
        reactivated_at=row["reactivated_at"],
        suspended_at=row["suspended_at"],
        canceled_at=row["canceled_at"],
        metadata=dict(row["metadata"] or {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_billing_cycle(row: dict[str, Any]) -> CommercialBillingCycleDetails:
    return CommercialBillingCycleDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        subscription_id=str(row["subscription_id"]),
        cycle_number=int(row["cycle_number"]),
        period_start_at=row["period_start_at"],
        period_end_at=row["period_end_at"],
        due_at=row["due_at"],
        amount=Decimal(str(row["amount"])),
        currency=str(row["currency"]),
        status=str(row["status"]),
        invoice_id=row["invoice_id"],
        provider_event_id=row["provider_event_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_billing_event(row: dict[str, Any]) -> CommercialBillingEventDetails:
    return CommercialBillingEventDetails(
        id=str(row["id"]),
        tenant_id=row["tenant_id"],
        subscription_id=row["subscription_id"],
        provider=str(row["provider"]),
        external_event_id=str(row["external_event_id"]),
        event_type=str(row["event_type"]),
        processing_status=str(row["processing_status"]),
        action_taken=row["action_taken"],
        error_message=row["error_message"],
        raw_payload=dict(row["raw_payload"] or {}),
        processed_at=row["processed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def ensure_default_plan(session: AsyncSession) -> CommercialPlanDetails:
    catalog = await ensure_plan_catalog(session)
    for plan in catalog:
        if plan.code == DEFAULT_COMMERCIAL_PLAN_CODE:
            return plan
    raise ValueError("Default commercial plan could not be ensured")


async def ensure_plan_catalog(session: AsyncSession) -> list[CommercialPlanDetails]:
    plans: list[CommercialPlanDetails] = []
    for definition in DEFAULT_PLAN_CATALOG:
        plans.append(
            await create_plan(
                session,
                code=str(definition["code"]),
                name=str(definition["name"]),
                description=definition["description"] if isinstance(definition["description"], str) else None,
                provider=str(definition["provider"]),
                provider_price_id=definition["provider_price_id"] if isinstance(definition["provider_price_id"], str) else None,
                billing_interval=str(definition["billing_interval"]),
                price_amount=Decimal(str(definition["price_amount"])),
                currency=str(definition["currency"]),
                trial_days=int(definition["trial_days"]),
                grace_days=int(definition["grace_days"]),
                is_active=bool(definition["is_active"]),
                features=dict(definition["features"]),
            )
        )
    return plans


async def create_plan(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    description: str | None,
    provider: str,
    provider_price_id: str | None,
    billing_interval: str,
    price_amount: Decimal,
    currency: str,
    trial_days: int,
    grace_days: int,
    is_active: bool,
    features: dict[str, Any],
) -> CommercialPlanDetails:
    result = await session.execute(
        text(
            """
            insert into public.commercial_plans (
                id,
                code,
                name,
                description,
                provider,
                provider_price_id,
                billing_interval,
                price_amount,
                currency,
                trial_days,
                grace_days,
                is_active,
                features
            )
            values (
                cast(:id as varchar),
                cast(:code as varchar),
                cast(:name as varchar),
                cast(:description as text),
                cast(:provider as varchar),
                cast(:provider_price_id as varchar),
                cast(:billing_interval as varchar),
                cast(:price_amount as numeric),
                cast(:currency as varchar),
                cast(:trial_days as integer),
                cast(:grace_days as integer),
                :is_active,
                cast(:features as jsonb)
            )
            on conflict (code) do update
              set name = excluded.name,
                  description = excluded.description,
                  provider = excluded.provider,
                  provider_price_id = excluded.provider_price_id,
                  billing_interval = excluded.billing_interval,
                  price_amount = excluded.price_amount,
                  currency = excluded.currency,
                  trial_days = excluded.trial_days,
                  grace_days = excluded.grace_days,
                  is_active = excluded.is_active,
                  features = excluded.features,
                  updated_at = now()
            returning
                id,
                code,
                name,
                description,
                provider,
                provider_price_id,
                billing_interval,
                price_amount,
                currency,
                trial_days,
                grace_days,
                is_active,
                features,
                created_at,
                updated_at
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "code": code.strip(),
            "name": name.strip(),
            "description": _clean_text(description),
            "provider": provider.strip().lower(),
            "provider_price_id": _clean_text(provider_price_id),
            "billing_interval": billing_interval.strip().lower(),
            "price_amount": price_amount,
            "currency": currency.strip().upper(),
            "trial_days": trial_days,
            "grace_days": grace_days,
            "is_active": is_active,
            "features": json.dumps(features or {}),
        },
    )
    return _row_to_plan(dict(result.mappings().one()))


async def list_plans(
    session: AsyncSession,
    *,
    include_inactive: bool = True,
) -> list[CommercialPlanDetails]:
    query = """
        select
            id,
            code,
            name,
            description,
            provider,
            provider_price_id,
            billing_interval,
            price_amount,
            currency,
            trial_days,
            grace_days,
            is_active,
            features,
            created_at,
            updated_at
        from public.commercial_plans
    """
    params: dict[str, Any] = {}
    if not include_inactive:
        query += " where is_active = true"
    query += " order by created_at asc"
    result = await session.execute(text(query), params)
    return [_row_to_plan(dict(row)) for row in result.mappings().all()]


async def get_plan_by_code(
    session: AsyncSession,
    *,
    code: str,
) -> CommercialPlanDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                code,
                name,
                description,
                provider,
                provider_price_id,
                billing_interval,
                price_amount,
                currency,
                trial_days,
                grace_days,
                is_active,
                features,
                created_at,
                updated_at
            from public.commercial_plans
            where code = cast(:code as varchar)
            """
        ),
        {"code": code.strip()},
    )
    row = result.mappings().first()
    return _row_to_plan(dict(row)) if row else None


async def get_plan_by_id(
    session: AsyncSession,
    *,
    plan_id: str,
) -> CommercialPlanDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                code,
                name,
                description,
                provider,
                provider_price_id,
                billing_interval,
                price_amount,
                currency,
                trial_days,
                grace_days,
                is_active,
                features,
                created_at,
                updated_at
            from public.commercial_plans
            where id = cast(:plan_id as varchar)
            """
        ),
        {"plan_id": plan_id},
    )
    row = result.mappings().first()
    return _row_to_plan(dict(row)) if row else None


async def get_plan_by_provider_price_id(
    session: AsyncSession,
    *,
    provider_price_id: str,
) -> CommercialPlanDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                code,
                name,
                description,
                provider,
                provider_price_id,
                billing_interval,
                price_amount,
                currency,
                trial_days,
                grace_days,
                is_active,
                features,
                created_at,
                updated_at
            from public.commercial_plans
            where provider_price_id = cast(:provider_price_id as varchar)
            limit 1
            """
        ),
        {"provider_price_id": provider_price_id},
    )
    row = result.mappings().first()
    return _row_to_plan(dict(row)) if row else None


async def update_plan(
    session: AsyncSession,
    *,
    code: str,
    name: str | None = None,
    description: str | None = None,
    provider: str | None = None,
    provider_price_id: str | None = None,
    billing_interval: str | None = None,
    price_amount: Decimal | None = None,
    currency: str | None = None,
    trial_days: int | None = None,
    grace_days: int | None = None,
    is_active: bool | None = None,
    features: dict[str, Any] | None = None,
) -> CommercialPlanDetails:
    existing = await get_plan_by_code(session, code=code)
    if not existing:
        raise ValueError(f"Commercial plan does not exist: {code}")

    result = await session.execute(
        text(
            """
            update public.commercial_plans
            set name = coalesce(cast(:name as varchar), name),
                description = coalesce(cast(:description as text), description),
                provider = coalesce(cast(:provider as varchar), provider),
                provider_price_id = coalesce(cast(:provider_price_id as varchar), provider_price_id),
                billing_interval = coalesce(cast(:billing_interval as varchar), billing_interval),
                price_amount = coalesce(cast(:price_amount as numeric), price_amount),
                currency = coalesce(cast(:currency as varchar), currency),
                trial_days = coalesce(cast(:trial_days as integer), trial_days),
                grace_days = coalesce(cast(:grace_days as integer), grace_days),
                is_active = coalesce(:is_active, is_active),
                features = coalesce(cast(:features as jsonb), features),
                updated_at = now()
            where code = cast(:code as varchar)
            returning
                id,
                code,
                name,
                description,
                provider,
                provider_price_id,
                billing_interval,
                price_amount,
                currency,
                trial_days,
                grace_days,
                is_active,
                features,
                created_at,
                updated_at
            """
        ),
        {
            "code": code.strip(),
            "name": name.strip() if name else None,
            "description": _clean_text(description),
            "provider": provider.strip().lower() if provider else None,
            "provider_price_id": _clean_text(provider_price_id),
            "billing_interval": (
                billing_interval.strip().lower() if billing_interval else None
            ),
            "price_amount": price_amount,
            "currency": currency.strip().upper() if currency else None,
            "trial_days": trial_days,
            "grace_days": grace_days,
            "is_active": is_active,
            "features": json.dumps(features) if features is not None else None,
        },
    )
    return _row_to_plan(dict(result.mappings().one()))


async def list_subscriptions(
    session: AsyncSession,
    *,
    tenant_id: str | None = None,
) -> list[CommercialSubscriptionDetails]:
    query = """
        select
            s.id,
            s.tenant_id,
            s.plan_id,
            p.code as plan_code,
            p.name as plan_name,
            s.provider,
            s.provider_customer_id,
            s.provider_subscription_id,
            s.subscription_status,
            s.commercial_state,
            s.state_reason,
            s.trial_start_at,
            s.trial_end_at,
            s.current_period_start_at,
            s.current_period_end_at,
            s.grace_end_at,
            s.cancel_at_period_end,
            s.activated_at,
            s.reactivated_at,
            s.suspended_at,
            s.canceled_at,
            s.metadata,
            s.created_at,
            s.updated_at
        from public.commercial_subscriptions s
        join public.commercial_plans p
          on p.id = s.plan_id
    """
    params: dict[str, Any] = {}
    if tenant_id:
        query += " where s.tenant_id = cast(:tenant_id as varchar)"
        params["tenant_id"] = tenant_id
    query += " order by s.created_at desc"
    result = await session.execute(text(query), params)
    return [_row_to_subscription(dict(row)) for row in result.mappings().all()]


async def get_subscription_by_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> CommercialSubscriptionDetails | None:
    result = await session.execute(
        text(
            """
            select
                s.id,
                s.tenant_id,
                s.plan_id,
                p.code as plan_code,
                p.name as plan_name,
                s.provider,
                s.provider_customer_id,
                s.provider_subscription_id,
                s.subscription_status,
                s.commercial_state,
                s.state_reason,
                s.trial_start_at,
                s.trial_end_at,
                s.current_period_start_at,
                s.current_period_end_at,
                s.grace_end_at,
                s.cancel_at_period_end,
                s.activated_at,
                s.reactivated_at,
                s.suspended_at,
                s.canceled_at,
                s.metadata,
                s.created_at,
                s.updated_at
            from public.commercial_subscriptions s
            join public.commercial_plans p
              on p.id = s.plan_id
            where s.tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first()
    return _row_to_subscription(dict(row)) if row else None


async def get_subscription_by_id(
    session: AsyncSession,
    *,
    subscription_id: str,
) -> CommercialSubscriptionDetails | None:
    result = await session.execute(
        text(
            """
            select
                s.id,
                s.tenant_id,
                s.plan_id,
                p.code as plan_code,
                p.name as plan_name,
                s.provider,
                s.provider_customer_id,
                s.provider_subscription_id,
                s.subscription_status,
                s.commercial_state,
                s.state_reason,
                s.trial_start_at,
                s.trial_end_at,
                s.current_period_start_at,
                s.current_period_end_at,
                s.grace_end_at,
                s.cancel_at_period_end,
                s.activated_at,
                s.reactivated_at,
                s.suspended_at,
                s.canceled_at,
                s.metadata,
                s.created_at,
                s.updated_at
            from public.commercial_subscriptions s
            join public.commercial_plans p
              on p.id = s.plan_id
            where s.id = cast(:subscription_id as varchar)
            """
        ),
        {"subscription_id": subscription_id},
    )
    row = result.mappings().first()
    return _row_to_subscription(dict(row)) if row else None


async def get_subscription_by_provider_subscription_id(
    session: AsyncSession,
    *,
    provider_subscription_id: str,
) -> CommercialSubscriptionDetails | None:
    result = await session.execute(
        text(
            """
            select
                s.id,
                s.tenant_id,
                s.plan_id,
                p.code as plan_code,
                p.name as plan_name,
                s.provider,
                s.provider_customer_id,
                s.provider_subscription_id,
                s.subscription_status,
                s.commercial_state,
                s.state_reason,
                s.trial_start_at,
                s.trial_end_at,
                s.current_period_start_at,
                s.current_period_end_at,
                s.grace_end_at,
                s.cancel_at_period_end,
                s.activated_at,
                s.reactivated_at,
                s.suspended_at,
                s.canceled_at,
                s.metadata,
                s.created_at,
                s.updated_at
            from public.commercial_subscriptions s
            join public.commercial_plans p
              on p.id = s.plan_id
            where s.provider_subscription_id = cast(:provider_subscription_id as varchar)
            """
        ),
        {"provider_subscription_id": provider_subscription_id},
    )
    row = result.mappings().first()
    return _row_to_subscription(dict(row)) if row else None


async def get_subscription_by_provider_customer_id(
    session: AsyncSession,
    *,
    provider_customer_id: str,
) -> CommercialSubscriptionDetails | None:
    result = await session.execute(
        text(
            """
            select
                s.id,
                s.tenant_id,
                s.plan_id,
                p.code as plan_code,
                p.name as plan_name,
                s.provider,
                s.provider_customer_id,
                s.provider_subscription_id,
                s.subscription_status,
                s.commercial_state,
                s.state_reason,
                s.trial_start_at,
                s.trial_end_at,
                s.current_period_start_at,
                s.current_period_end_at,
                s.grace_end_at,
                s.cancel_at_period_end,
                s.activated_at,
                s.reactivated_at,
                s.suspended_at,
                s.canceled_at,
                s.metadata,
                s.created_at,
                s.updated_at
            from public.commercial_subscriptions s
            join public.commercial_plans p
              on p.id = s.plan_id
            where s.provider_customer_id = cast(:provider_customer_id as varchar)
            order by s.updated_at desc
            limit 1
            """
        ),
        {"provider_customer_id": provider_customer_id},
    )
    row = result.mappings().first()
    return _row_to_subscription(dict(row)) if row else None


async def list_billing_cycles(
    session: AsyncSession,
    *,
    tenant_id: str,
    subscription_id: str | None = None,
    limit: int = 5,
) -> list[CommercialBillingCycleDetails]:
    query = """
        select
            id,
            tenant_id,
            subscription_id,
            cycle_number,
            period_start_at,
            period_end_at,
            due_at,
            amount,
            currency,
            status,
            invoice_id,
            provider_event_id,
            created_at,
            updated_at
        from public.commercial_billing_cycles
        where tenant_id = cast(:tenant_id as varchar)
    """
    params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit}
    if subscription_id:
        query += " and subscription_id = cast(:subscription_id as varchar)"
        params["subscription_id"] = subscription_id
    query += " order by period_end_at desc, created_at desc limit cast(:limit as integer)"
    result = await session.execute(text(query), params)
    return [_row_to_billing_cycle(dict(row)) for row in result.mappings().all()]


async def list_billing_events(
    session: AsyncSession,
    *,
    tenant_id: str,
    subscription_id: str | None = None,
    limit: int = 5,
) -> list[CommercialBillingEventDetails]:
    query = """
        select
            id,
            tenant_id,
            subscription_id,
            provider,
            external_event_id,
            event_type,
            processing_status,
            action_taken,
            error_message,
            raw_payload,
            processed_at,
            created_at,
            updated_at
        from public.commercial_billing_events
        where tenant_id = cast(:tenant_id as varchar)
    """
    params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit}
    if subscription_id:
        query += " and subscription_id = cast(:subscription_id as varchar)"
        params["subscription_id"] = subscription_id
    query += " order by created_at desc limit cast(:limit as integer)"
    result = await session.execute(text(query), params)
    return [_row_to_billing_event(dict(row)) for row in result.mappings().all()]


async def get_subscription_summary_by_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    limit: int = 5,
) -> CommercialSubscriptionSummary:
    subscription = await get_subscription_by_tenant(session, tenant_id=tenant_id)
    subscription_id = subscription.id if subscription else None
    recent_billing_cycles = await list_billing_cycles(
        session,
        tenant_id=tenant_id,
        subscription_id=subscription_id,
        limit=limit,
    )
    recent_billing_events = await list_billing_events(
        session,
        tenant_id=tenant_id,
        subscription_id=subscription_id,
        limit=limit,
    )
    return CommercialSubscriptionSummary(
        subscription=subscription,
        recent_billing_cycles=recent_billing_cycles,
        recent_billing_events=recent_billing_events,
    )


async def get_tenant_commercial_status(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> TenantCommercialStatus:
    subscription = await get_subscription_by_tenant(session, tenant_id=tenant_id)
    plan = await get_plan_by_id(session, plan_id=subscription.plan_id) if subscription else None

    trial_status = "not_applicable"
    if subscription and subscription.trial_end_at is not None:
        trial_status = "active" if subscription.trial_end_at >= _now() else "ended"
    elif subscription and subscription.subscription_status in {"trialing", "trial"}:
        trial_status = "active"
    elif subscription and subscription.commercial_state == "trial":
        trial_status = "active"

    next_billing_at = subscription.current_period_end_at if subscription else None
    renewal_at = subscription.current_period_end_at if subscription else None
    provider = subscription.provider if subscription else None

    return TenantCommercialStatus(
        current_plan=plan,
        subscription=subscription,
        subscription_status=subscription.subscription_status if subscription else None,
        trial_status=trial_status,
        next_billing_at=next_billing_at,
        renewal_at=renewal_at,
        provider=provider,
        provider_name=PROVIDER_DISPLAY_NAMES.get(provider) if provider else None,
        provider_customer_id=subscription.provider_customer_id if subscription else None,
        provider_subscription_id=subscription.provider_subscription_id if subscription else None,
        commercially_active=is_commercially_active(
            subscription.subscription_status if subscription else None,
            provider=provider,
            commercial_state=subscription.commercial_state if subscription else None,
        ),
    )


def _provider_config_from_settings(provider_settings: Any) -> dict[str, Any]:
    return {
        "secret_key": provider_settings.secret_key,
        "api_key": provider_settings.api_key,
        "client_secret": provider_settings.client_secret,
        "webhook_secret": provider_settings.webhook_secret,
        "publishable_key": provider_settings.publishable_key,
        "account_id": provider_settings.account_id,
        "merchant_id": provider_settings.merchant_id,
        "client_id": provider_settings.client_id,
        "mode": provider_settings.mode,
    }


async def _get_tenant_provider_client(
    session: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
):
    provider_settings = await get_payment_gateway_provider_record(
        session,
        tenant_id=tenant_id,
        provider=provider,
    )
    if not provider_settings.is_enabled:
        raise ValueError(f"Payment provider is not enabled for tenant: {provider}")
    if provider_settings.configuration_state != "configured":
        raise ValueError(f"Payment provider is not fully configured for tenant: {provider}")
    return get_commercial_provider(provider, config=_provider_config_from_settings(provider_settings))


def _build_checkout_urls(*, tenant_id: str, mode: str) -> tuple[str, str]:
    base_url = settings.FRONTEND_BASE_URL.strip().rstrip("/") or "http://localhost:3000"
    path = "/finance/payments/subscription-billing"
    success_url = f"{base_url}{path}?checkout={mode}_success&tenant={tenant_id}"
    cancel_url = f"{base_url}{path}?checkout={mode}_canceled&tenant={tenant_id}"
    return success_url, cancel_url


async def _set_tenant_access_state(
    session: AsyncSession,
    *,
    tenant_id: str,
    commercial_state: str,
    reason: str | None,
) -> None:
    tenant_status, is_active = _commercial_state_to_tenant_status(commercial_state)
    await session.execute(
        text(
            """
            update public.tenants
            set status = cast(:tenant_status as varchar),
                status_reason = cast(:status_reason as varchar),
                is_active = :is_active,
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "tenant_status": tenant_status,
            "status_reason": reason,
            "is_active": is_active,
        },
    )
    await auth_cache.invalidate_snapshots_for_tenant(tenant_id)


async def _upsert_subscription(
    session: AsyncSession,
    *,
    tenant_id: str,
    plan_id: str,
    provider: str,
    subscription_status: str | None,
    commercial_state: str,
    provider_customer_id: str | None,
    provider_subscription_id: str | None,
    state_reason: str | None,
    trial_start_at: datetime | None,
    trial_end_at: datetime | None,
    current_period_start_at: datetime | None,
    current_period_end_at: datetime | None,
    grace_end_at: datetime | None,
    cancel_at_period_end: bool,
    activated_at: datetime | None,
    reactivated_at: datetime | None,
    suspended_at: datetime | None,
    canceled_at: datetime | None,
    metadata: dict[str, Any],
) -> CommercialSubscriptionDetails:
    result = await session.execute(
        text(
            """
            with upserted as (
                insert into public.commercial_subscriptions (
                    id,
                    tenant_id,
                    plan_id,
                    provider,
                    provider_customer_id,
                    provider_subscription_id,
                    subscription_status,
                    commercial_state,
                    state_reason,
                    trial_start_at,
                    trial_end_at,
                    current_period_start_at,
                    current_period_end_at,
                    grace_end_at,
                    cancel_at_period_end,
                    activated_at,
                    reactivated_at,
                    suspended_at,
                    canceled_at,
                    metadata
                )
                values (
                    cast(:id as varchar),
                    cast(:tenant_id as varchar),
                    cast(:plan_id as varchar),
                    cast(:provider as varchar),
                    cast(:provider_customer_id as varchar),
                    cast(:provider_subscription_id as varchar),
                    cast(:subscription_status as varchar),
                    cast(:commercial_state as varchar),
                    cast(:state_reason as varchar),
                    :trial_start_at,
                    :trial_end_at,
                    :current_period_start_at,
                    :current_period_end_at,
                    :grace_end_at,
                    :cancel_at_period_end,
                    :activated_at,
                    :reactivated_at,
                    :suspended_at,
                    :canceled_at,
                    cast(:metadata as jsonb)
                )
                on conflict (tenant_id) do update
                  set plan_id = excluded.plan_id,
                      provider = excluded.provider,
                      provider_customer_id = excluded.provider_customer_id,
                      provider_subscription_id = excluded.provider_subscription_id,
                      subscription_status = excluded.subscription_status,
                      commercial_state = excluded.commercial_state,
                      state_reason = excluded.state_reason,
                      trial_start_at = excluded.trial_start_at,
                      trial_end_at = excluded.trial_end_at,
                      current_period_start_at = excluded.current_period_start_at,
                      current_period_end_at = excluded.current_period_end_at,
                      grace_end_at = excluded.grace_end_at,
                      cancel_at_period_end = excluded.cancel_at_period_end,
                      activated_at = excluded.activated_at,
                      reactivated_at = excluded.reactivated_at,
                      suspended_at = excluded.suspended_at,
                      canceled_at = excluded.canceled_at,
                      metadata = excluded.metadata,
                      updated_at = now()
                returning
                    id,
                    tenant_id,
                    plan_id,
                    provider,
                    provider_customer_id,
                    provider_subscription_id,
                    subscription_status,
                    commercial_state,
                    state_reason,
                    trial_start_at,
                    trial_end_at,
                    current_period_start_at,
                    current_period_end_at,
                    grace_end_at,
                    cancel_at_period_end,
                    activated_at,
                    reactivated_at,
                    suspended_at,
                    canceled_at,
                    metadata,
                    created_at,
                    updated_at
            )
            select
                u.id,
                u.tenant_id,
                u.plan_id,
                p.code as plan_code,
                p.name as plan_name,
                u.provider,
                u.provider_customer_id,
                u.provider_subscription_id,
                u.subscription_status,
                u.commercial_state,
                u.state_reason,
                u.trial_start_at,
                u.trial_end_at,
                u.current_period_start_at,
                u.current_period_end_at,
                u.grace_end_at,
                u.cancel_at_period_end,
                u.activated_at,
                u.reactivated_at,
                u.suspended_at,
                u.canceled_at,
                u.metadata,
                u.created_at,
                u.updated_at
            from upserted u
            join public.commercial_plans p
              on p.id = u.plan_id
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "provider": provider,
            "provider_customer_id": provider_customer_id,
            "provider_subscription_id": provider_subscription_id,
            "subscription_status": _normalize_subscription_status(subscription_status),
            "commercial_state": commercial_state,
            "state_reason": state_reason,
            "trial_start_at": trial_start_at,
            "trial_end_at": trial_end_at,
            "current_period_start_at": current_period_start_at,
            "current_period_end_at": current_period_end_at,
            "grace_end_at": grace_end_at,
            "cancel_at_period_end": cancel_at_period_end,
            "activated_at": activated_at,
            "reactivated_at": reactivated_at,
            "suspended_at": suspended_at,
            "canceled_at": canceled_at,
            "metadata": json.dumps(metadata or {}),
        },
    )
    return _row_to_subscription(dict(result.mappings().one()))


async def bootstrap_tenant_subscription(
    session: AsyncSession,
    *,
    tenant_id: str,
    plan_code: str = DEFAULT_COMMERCIAL_PLAN_CODE,
    provider: str = DEFAULT_COMMERCIAL_PROVIDER,
    start_trial: bool = True,
    customer_email: str | None = None,
    customer_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> CommercialSubscriptionDetails:
    plan = await get_plan_by_code(session, code=plan_code)
    if not plan:
        raise ValueError(f"Commercial plan does not exist: {plan_code}")
    if not plan.is_active:
        raise ValueError(f"Commercial plan is inactive: {plan_code}")
    existing_subscription = await get_subscription_by_tenant(session, tenant_id=tenant_id)

    effective_provider = (provider or plan.provider).strip().lower()

    if not plan.provider_price_id and not start_trial:
        raise ValueError(f"Commercial plan is missing provider_price_id: {plan.code}")

    request_now = _now()
    customer_id: str | None = None
    subscription_result = CommercialProviderSubscriptionResult(
        provider=effective_provider,
        provider_customer_id=None,
        provider_subscription_id=None,
        status="trial" if start_trial else "pending",
        trial_end_at=(
            request_now + timedelta(days=plan.trial_days) if start_trial else None
        ),
        current_period_start_at=request_now,
        current_period_end_at=request_now
        + timedelta(days=plan.trial_days if start_trial else 30),
        cancel_at_period_end=False,
        raw={"trial_only": start_trial},
    )

    if plan.provider_price_id:
        provider_client = await _get_tenant_provider_client(
            session,
            tenant_id=tenant_id,
            provider=effective_provider,
        )
        if not start_trial:
            default_payment_method = await get_default_payment_method(session, tenant_id=tenant_id)
            if not default_payment_method:
                raise ValueError("A default payment method is required before starting a paid subscription")
        customer_id = existing_subscription.provider_customer_id if existing_subscription else None
        if not customer_id:
            customer_id = await provider_client.create_customer(
                email=customer_email or f"billing+{tenant_id}@supacrm.local",
                metadata={
                    "tenant_id": tenant_id,
                    "plan_code": plan.code,
                    **(metadata or {}),
                },
            )
        subscription_result = await provider_client.create_subscription(
            customer_id=customer_id,
            price_id=plan.provider_price_id,
            metadata={
                "tenant_id": tenant_id,
                "plan_code": plan.code,
                **(metadata or {}),
            },
            trial_days=plan.trial_days if start_trial else 0,
        )

    subscription = await _upsert_subscription(
        session,
        tenant_id=tenant_id,
        plan_id=plan.id,
        provider=effective_provider,
        subscription_status=subscription_result.status,
        commercial_state=(
            "pending"
            if plan.provider_price_id
            else (
                "trial"
                if subscription_result.status in {"trial", "trialing"} or start_trial
                else "active"
            )
        ),
        provider_customer_id=subscription_result.provider_customer_id or customer_id,
        provider_subscription_id=subscription_result.provider_subscription_id,
        state_reason="awaiting_stripe_webhook_confirmation" if plan.provider_price_id else None,
        trial_start_at=request_now if start_trial else None,
        trial_end_at=subscription_result.trial_end_at,
        current_period_start_at=subscription_result.current_period_start_at,
        current_period_end_at=subscription_result.current_period_end_at,
        grace_end_at=None,
        cancel_at_period_end=subscription_result.cancel_at_period_end,
        activated_at=None if plan.provider_price_id else request_now,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={"provider_raw": subscription_result.raw, **(metadata or {})},
    )
    await _set_tenant_access_state(session, tenant_id=tenant_id, commercial_state=subscription.commercial_state, reason=subscription.state_reason)
    return subscription


async def change_subscription_state(
    session: AsyncSession,
    *,
    subscription_id: str,
    commercial_state: str,
    subscription_status: str | None = None,
    reason: str | None = None,
    plan_id: str | None = None,
    provider_subscription_id: str | None = None,
    provider_customer_id: str | None = None,
    trial_end_at: datetime | None = None,
    current_period_start_at: datetime | None = None,
    current_period_end_at: datetime | None = None,
    grace_end_at: datetime | None = None,
    clear_grace_end_at: bool = False,
    cancel_at_period_end: bool | None = None,
) -> CommercialSubscriptionDetails:
    subscription = await get_subscription_by_id(
        session,
        subscription_id=subscription_id,
    )
    if not subscription:
        raise ValueError(f"Subscription does not exist: {subscription_id}")

    normalized_state = _normalize_state(commercial_state)
    now = _now()

    updated = await session.execute(
        text(
            """
            with updated_subscription as (
                update public.commercial_subscriptions
                set plan_id = coalesce(cast(:plan_id as varchar), plan_id),
                    provider_subscription_id = coalesce(
                        cast(:provider_subscription_id as varchar),
                        provider_subscription_id
                    ),
                    provider_customer_id = coalesce(
                        cast(:provider_customer_id as varchar),
                        provider_customer_id
                    ),
                    subscription_status = coalesce(
                        cast(:subscription_status as varchar),
                        subscription_status
                    ),
                    commercial_state = cast(:commercial_state as varchar),
                    state_reason = cast(:state_reason as varchar),
                    trial_end_at = coalesce(:trial_end_at, trial_end_at),
                    current_period_start_at = coalesce(
                        :current_period_start_at,
                        current_period_start_at
                    ),
                    current_period_end_at = coalesce(
                        :current_period_end_at,
                        current_period_end_at
                    ),
                    grace_end_at = case
                        when :clear_grace_end_at then null
                        else coalesce(:grace_end_at, grace_end_at)
                    end,
                    cancel_at_period_end = coalesce(
                        :cancel_at_period_end,
                        cancel_at_period_end
                    ),
                    activated_at = case
                        when :commercial_state = 'active'
                            then coalesce(activated_at, :now)
                        else activated_at
                    end,
                    reactivated_at = case
                        when :commercial_state = 'active' and activated_at is not null
                            then :now
                        else reactivated_at
                    end,
                    suspended_at = case
                        when :commercial_state = 'suspended'
                            then coalesce(suspended_at, :now)
                        else suspended_at
                    end,
                    canceled_at = case
                        when :commercial_state = 'canceled'
                            then coalesce(canceled_at, :now)
                        else canceled_at
                    end,
                    updated_at = :now
                where id = cast(:subscription_id as varchar)
                returning
                    id,
                    tenant_id,
                    plan_id,
                    provider,
                    provider_customer_id,
                    provider_subscription_id,
                    subscription_status,
                    commercial_state,
                    state_reason,
                    trial_start_at,
                    trial_end_at,
                    current_period_start_at,
                    current_period_end_at,
                    grace_end_at,
                    cancel_at_period_end,
                    activated_at,
                    reactivated_at,
                    suspended_at,
                    canceled_at,
                    metadata,
                    created_at,
                    updated_at
            )
            select
                u.id,
                u.tenant_id,
                u.plan_id,
                p.code as plan_code,
                p.name as plan_name,
                u.provider,
                u.provider_customer_id,
                u.provider_subscription_id,
                u.subscription_status,
                u.commercial_state,
                u.state_reason,
                u.trial_start_at,
                u.trial_end_at,
                u.current_period_start_at,
                u.current_period_end_at,
                u.grace_end_at,
                u.cancel_at_period_end,
                u.activated_at,
                u.reactivated_at,
                u.suspended_at,
                u.canceled_at,
                u.metadata,
                u.created_at,
                u.updated_at
            from updated_subscription u
            join public.commercial_plans p
              on p.id = u.plan_id
            """
        ),
        {
            "subscription_id": subscription_id,
            "plan_id": plan_id,
            "provider_subscription_id": provider_subscription_id,
            "provider_customer_id": provider_customer_id,
            "subscription_status": _normalize_subscription_status(subscription_status),
            "commercial_state": normalized_state,
            "state_reason": _clean_text(reason),
            "trial_end_at": trial_end_at,
            "current_period_start_at": current_period_start_at,
            "current_period_end_at": current_period_end_at,
            "grace_end_at": grace_end_at,
            "clear_grace_end_at": clear_grace_end_at,
            "cancel_at_period_end": cancel_at_period_end,
            "now": now,
        },
    )
    row = updated.mappings().one()
    await _set_tenant_access_state(
        session,
        tenant_id=subscription.tenant_id,
        commercial_state=normalized_state,
        reason=reason,
    )
    return _row_to_subscription(dict(row))


async def suspend_subscription(
    session: AsyncSession,
    *,
    subscription_id: str,
    reason: str | None = None,
) -> CommercialSubscriptionDetails:
    return await change_subscription_state(
        session,
        subscription_id=subscription_id,
        commercial_state="suspended",
        reason=reason,
    )


async def reactivate_subscription(
    session: AsyncSession,
    *,
    subscription_id: str,
    reason: str | None = None,
) -> CommercialSubscriptionDetails:
    return await change_subscription_state(
        session,
        subscription_id=subscription_id,
        subscription_status="active",
        commercial_state="active",
        reason=reason,
    )


async def cancel_subscription(
    session: AsyncSession,
    *,
    subscription_id: str,
    reason: str | None = None,
) -> CommercialSubscriptionDetails:
    return await change_subscription_state(
        session,
        subscription_id=subscription_id,
        subscription_status="canceled",
        commercial_state="canceled",
        reason=reason,
    )


async def set_subscription_past_due(
    session: AsyncSession,
    *,
    subscription_id: str,
    reason: str | None = None,
    grace_days: int = DEFAULT_GRACE_DAYS,
) -> CommercialSubscriptionDetails:
    subscription = await get_subscription_by_id(
        session,
        subscription_id=subscription_id,
    )
    if not subscription:
        raise ValueError(f"Subscription does not exist: {subscription_id}")

    plan = await get_plan_by_id(session, plan_id=subscription.plan_id)
    effective_grace_days = plan.grace_days if plan else grace_days
    grace_end_at = _now() + timedelta(days=effective_grace_days)

    return await change_subscription_state(
        session,
        subscription_id=subscription_id,
        subscription_status="past_due",
        commercial_state="past_due",
        reason=reason,
        grace_end_at=grace_end_at,
    )


async def mark_subscription_grace(
    session: AsyncSession,
    *,
    subscription_id: str,
    reason: str | None = None,
    grace_end_at: datetime | None = None,
) -> CommercialSubscriptionDetails:
    return await change_subscription_state(
        session,
        subscription_id=subscription_id,
        subscription_status="grace",
        commercial_state="grace",
        reason=reason,
        grace_end_at=grace_end_at or (_now() + timedelta(days=DEFAULT_GRACE_DAYS)),
    )


async def ensure_billing_cycle(
    session: AsyncSession,
    *,
    subscription_id: str,
    cycle_number: int,
    period_start_at: datetime,
    period_end_at: datetime,
    due_at: datetime,
    amount: Decimal,
    currency: str,
    status: str = "pending",
    invoice_id: str | None = None,
    provider_event_id: str | None = None,
) -> CommercialBillingCycleDetails:
    subscription = await get_subscription_by_id(
        session,
        subscription_id=subscription_id,
    )
    if not subscription:
        raise ValueError(f"Subscription does not exist: {subscription_id}")

    result = await session.execute(
        text(
            """
            insert into public.commercial_billing_cycles (
                id,
                tenant_id,
                subscription_id,
                cycle_number,
                period_start_at,
                period_end_at,
                due_at,
                amount,
                currency,
                status,
                invoice_id,
                provider_event_id
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:subscription_id as varchar),
                cast(:cycle_number as integer),
                :period_start_at,
                :period_end_at,
                :due_at,
                cast(:amount as numeric),
                cast(:currency as varchar),
                cast(:status as varchar),
                cast(:invoice_id as varchar),
                cast(:provider_event_id as varchar)
            )
            on conflict (subscription_id, cycle_number) do update
              set period_start_at = excluded.period_start_at,
                  period_end_at = excluded.period_end_at,
                  due_at = excluded.due_at,
                  amount = excluded.amount,
                  currency = excluded.currency,
                  status = excluded.status,
                  invoice_id = excluded.invoice_id,
                  provider_event_id = excluded.provider_event_id,
                  updated_at = now()
            returning
                id,
                tenant_id,
                subscription_id,
                cycle_number,
                period_start_at,
                period_end_at,
                due_at,
                amount,
                currency,
                status,
                invoice_id,
                provider_event_id,
                created_at,
                updated_at
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": subscription.tenant_id,
            "subscription_id": subscription_id,
            "cycle_number": cycle_number,
            "period_start_at": period_start_at,
            "period_end_at": period_end_at,
            "due_at": due_at,
            "amount": amount,
            "currency": currency.strip().upper(),
            "status": status,
            "invoice_id": invoice_id,
            "provider_event_id": provider_event_id,
        },
    )
    return _row_to_billing_cycle(dict(result.mappings().one()))


async def ensure_billing_event(
    session: AsyncSession,
    *,
    provider: str,
    external_event_id: str,
    event_type: str,
    raw_payload: dict[str, Any],
    tenant_id: str | None = None,
    subscription_id: str | None = None,
    processing_status: str = "received",
    action_taken: str | None = None,
    error_message: str | None = None,
) -> CommercialBillingEventDetails:
    result = await session.execute(
        text(
            """
            insert into public.commercial_billing_events (
                id,
                tenant_id,
                subscription_id,
                provider,
                external_event_id,
                event_type,
                processing_status,
                action_taken,
                error_message,
                raw_payload
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:subscription_id as varchar),
                cast(:provider as varchar),
                cast(:external_event_id as varchar),
                cast(:event_type as varchar),
                cast(:processing_status as varchar),
                cast(:action_taken as varchar),
                cast(:error_message as text),
                cast(:raw_payload as jsonb)
            )
            on conflict (provider, external_event_id) do update
              set tenant_id = coalesce(
                      excluded.tenant_id,
                      public.commercial_billing_events.tenant_id
                  ),
                  subscription_id = coalesce(
                      excluded.subscription_id,
                      public.commercial_billing_events.subscription_id
                  ),
                  event_type = excluded.event_type,
                  processing_status = case
                      when public.commercial_billing_events.processing_status = 'processed'
                           and excluded.processing_status <> 'processed'
                          then public.commercial_billing_events.processing_status
                      else excluded.processing_status
                  end,
                  action_taken = case
                      when public.commercial_billing_events.processing_status = 'processed'
                           and excluded.processing_status <> 'processed'
                          then public.commercial_billing_events.action_taken
                      else excluded.action_taken
                  end,
                  error_message = case
                      when public.commercial_billing_events.processing_status = 'processed'
                           and excluded.processing_status <> 'processed'
                          then public.commercial_billing_events.error_message
                      else excluded.error_message
                  end,
                  raw_payload = case
                      when public.commercial_billing_events.processing_status = 'processed'
                           and excluded.processing_status <> 'processed'
                          then public.commercial_billing_events.raw_payload
                      else excluded.raw_payload
                  end,
                  processed_at = case
                      when excluded.processing_status = 'processed' then now()
                      else public.commercial_billing_events.processed_at
                  end,
                  updated_at = now()
            returning
                id,
                tenant_id,
                subscription_id,
                provider,
                external_event_id,
                event_type,
                processing_status,
                action_taken,
                error_message,
                raw_payload,
                processed_at,
                created_at,
                updated_at
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,
            "provider": provider,
            "external_event_id": external_event_id,
            "event_type": event_type,
            "processing_status": processing_status,
            "action_taken": action_taken,
            "error_message": error_message,
            "raw_payload": json.dumps(raw_payload),
        },
    )
    return _row_to_billing_event(dict(result.mappings().one()))


async def get_billing_event_by_external_event_id(
    session: AsyncSession,
    *,
    provider: str,
    external_event_id: str,
) -> CommercialBillingEventDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                subscription_id,
                provider,
                external_event_id,
                event_type,
                processing_status,
                action_taken,
                error_message,
                raw_payload,
                processed_at,
                created_at,
                updated_at
            from public.commercial_billing_events
            where provider = cast(:provider as varchar)
              and external_event_id = cast(:external_event_id as varchar)
            limit 1
            """
        ),
        {"provider": provider, "external_event_id": external_event_id},
    )
    row = result.mappings().first()
    return _row_to_billing_event(dict(row)) if row else None


def _event_object(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return {}
    raw_object = data.get("object", {})
    return raw_object if isinstance(raw_object, dict) else {}


def _event_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = _event_object(payload).get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _extract_price_id_from_payload(payload: dict[str, Any]) -> str | None:
    obj = _event_object(payload)
    items = obj.get("items", {})
    if isinstance(items, dict):
        data = items.get("data", [])
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                price = item.get("price", {})
                if isinstance(price, dict) and price.get("id"):
                    return str(price["id"])
    lines = obj.get("lines", {})
    if isinstance(lines, dict):
        data = lines.get("data", [])
        if isinstance(data, list):
            for line in data:
                if not isinstance(line, dict):
                    continue
                price = line.get("price", {})
                if isinstance(price, dict) and price.get("id"):
                    return str(price["id"])
    return None


def _require_event_subscription(
    subscription: CommercialSubscriptionDetails | None,
    *,
    event_type: str,
) -> CommercialSubscriptionDetails:
    if not subscription:
        raise ValueError(f"Subscription not found for webhook event: {event_type}")
    return subscription


async def process_provider_event(
    session: AsyncSession,
    event: CommercialWebhookEvent,
) -> CommercialBillingEventDetails:
    payload = event.raw_payload
    metadata = _event_metadata(payload)
    obj = _event_object(payload)
    tenant_id = metadata.get("tenant_id")
    local_subscription_id = metadata.get("subscription_id")

    subscription = None
    if local_subscription_id:
        subscription = await get_subscription_by_id(session, subscription_id=str(local_subscription_id))
    if not subscription and event.subscription_id:
        subscription = await get_subscription_by_provider_subscription_id(
            session,
            provider_subscription_id=str(event.subscription_id),
        )
    if not subscription and event.customer_id:
        subscription = await get_subscription_by_provider_customer_id(
            session,
            provider_customer_id=str(event.customer_id),
        )
    if not subscription and tenant_id:
        subscription = await get_subscription_by_tenant(session, tenant_id=str(tenant_id))

    existing_event = await get_billing_event_by_external_event_id(
        session,
        provider=event.provider,
        external_event_id=event.event_id,
    )
    if existing_event and existing_event.processing_status == "processed":
        return existing_event

    processing_event = await ensure_billing_event(
        session,
        provider=event.provider,
        external_event_id=event.event_id,
        event_type=event.event_type,
        raw_payload=payload,
        tenant_id=subscription.tenant_id if subscription else tenant_id,
        subscription_id=subscription.id if subscription else (str(local_subscription_id) if local_subscription_id else None),
        processing_status="processing",
    )
    if processing_event.processing_status == "processed":
        return processing_event

    try:
        action_taken = "ignored"
        normalized_type = event.event_type.lower()

        async with session.begin_nested():
            if normalized_type == "checkout.session.completed":
                mode = str(obj.get("mode") or "").lower()
                if mode not in {"setup", "subscription"}:
                    raise ValueError(f"Unsupported Stripe checkout session mode: {mode or 'missing'}")
                provider_customer_id = str(obj.get("customer") or event.customer_id or "") or None
                provider_subscription_id = str(obj.get("subscription") or event.subscription_id or "") or None
                subscription = _require_event_subscription(subscription, event_type=event.event_type)

                if provider_customer_id:
                    subscription = await change_subscription_state(
                        session,
                        subscription_id=subscription.id,
                        subscription_status=subscription.subscription_status,
                        commercial_state=subscription.commercial_state,
                        provider_customer_id=provider_customer_id,
                        provider_subscription_id=provider_subscription_id or subscription.provider_subscription_id,
                        reason=subscription.state_reason,
                    )

                if mode == "setup":
                    if not provider_customer_id or not obj.get("setup_intent"):
                        raise ValueError("Stripe setup checkout payload is missing customer or setup_intent")
                    provider_client = await _get_tenant_provider_client(
                        session,
                        tenant_id=subscription.tenant_id,
                        provider=subscription.provider,
                    )
                    setup_intent = await provider_client.get_setup_intent(
                        setup_intent_id=str(obj["setup_intent"]),
                    )
                    stripe_payment_method_id = setup_intent.get("payment_method")
                    if not stripe_payment_method_id:
                        raise ValueError("Stripe setup intent completed without a payment method")
                    pm_data = await provider_client.get_payment_method(
                        payment_method_id=str(stripe_payment_method_id),
                    )
                    await provider_client.set_default_payment_method(
                        customer_id=provider_customer_id,
                        payment_method_id=str(stripe_payment_method_id),
                    )
                    card_details = pm_data.get("card", {}) if isinstance(pm_data, dict) else {}
                    billing_details = pm_data.get("billing_details", {}) if isinstance(pm_data, dict) else {}
                    await create_payment_method(
                        session,
                        tenant_id=subscription.tenant_id,
                        provider_customer_id=provider_customer_id,
                        provider_payment_method_id=str(stripe_payment_method_id),
                        provider_type=subscription.provider,
                        card_brand=card_details.get("brand"),
                        card_last4=card_details.get("last4"),
                        card_exp_month=card_details.get("exp_month"),
                        card_exp_year=card_details.get("exp_year"),
                        billing_email=billing_details.get("email"),
                        billing_name=billing_details.get("name"),
                        is_default=True,
                        metadata={"provider_raw": pm_data, "setup_intent_id": obj.get("setup_intent")},
                    )
                    action_taken = "payment_method_captured"
                elif mode == "subscription":
                    subscription = await change_subscription_state(
                        session,
                        subscription_id=subscription.id,
                        subscription_status=subscription.subscription_status,
                        commercial_state=subscription.commercial_state,
                        provider_customer_id=provider_customer_id or subscription.provider_customer_id,
                        provider_subscription_id=provider_subscription_id or subscription.provider_subscription_id,
                        reason=subscription.state_reason,
                    )
                    action_taken = "checkout_completed"

            elif normalized_type in {"customer.subscription.created", "customer.subscription.updated"}:
                subscription = _require_event_subscription(subscription, event_type=event.event_type)

                raw_provider_status = obj.get("status")
                if not isinstance(raw_provider_status, str) or not raw_provider_status.strip():
                    raise ValueError("Stripe subscription payload is missing status")
                provider_status = raw_provider_status.strip().lower()
                matched_plan = None
                price_id = _extract_price_id_from_payload(payload)
                if price_id:
                    matched_plan = await get_plan_by_provider_price_id(session, provider_price_id=price_id)

                next_state = derive_commercial_state(
                    provider=subscription.provider,
                    subscription_status=provider_status,
                    commercial_state=subscription.commercial_state,
                )
                subscription = await change_subscription_state(
                    session,
                    subscription_id=subscription.id,
                    plan_id=matched_plan.id if matched_plan else None,
                    subscription_status=provider_status,
                    commercial_state=next_state,
                    reason=obj.get("cancellation_details", {}).get("comment") if isinstance(obj.get("cancellation_details"), dict) else None,
                    provider_subscription_id=event.subscription_id or subscription.provider_subscription_id,
                    provider_customer_id=event.customer_id or subscription.provider_customer_id,
                    trial_end_at=_extract_timestamp(payload, "trial_end"),
                    current_period_start_at=_extract_timestamp(payload, "current_period_start"),
                    current_period_end_at=_extract_timestamp(payload, "current_period_end"),
                    clear_grace_end_at=next_state not in {"past_due", "grace"},
                    cancel_at_period_end=bool(obj.get("cancel_at_period_end", False)),
                )
                action_taken = next_state

            elif normalized_type == "customer.subscription.deleted":
                subscription = _require_event_subscription(subscription, event_type=event.event_type)

                subscription = await change_subscription_state(
                    session,
                    subscription_id=subscription.id,
                    subscription_status="canceled",
                    commercial_state="canceled",
                    reason="subscription_deleted",
                    provider_subscription_id=event.subscription_id or subscription.provider_subscription_id,
                    provider_customer_id=event.customer_id or subscription.provider_customer_id,
                    clear_grace_end_at=True,
                    cancel_at_period_end=bool(obj.get("cancel_at_period_end", False)),
                )
                action_taken = "canceled"

            elif normalized_type == "invoice.payment_failed":
                subscription = _require_event_subscription(subscription, event_type=event.event_type)

                plan = await get_plan_by_id(session, plan_id=subscription.plan_id)
                subscription = await change_subscription_state(
                    session,
                    subscription_id=subscription.id,
                    subscription_status="past_due",
                    commercial_state="past_due",
                    reason="invoice_payment_failed",
                    grace_end_at=_now() + timedelta(days=(plan.grace_days if plan else DEFAULT_GRACE_DAYS)),
                )
                action_taken = "past_due"

            elif normalized_type == "invoice.payment_succeeded":
                subscription = _require_event_subscription(subscription, event_type=event.event_type)

                price_id = _extract_price_id_from_payload(payload)
                matched_plan = await get_plan_by_provider_price_id(session, provider_price_id=price_id) if price_id else None
                subscription = await change_subscription_state(
                    session,
                    subscription_id=subscription.id,
                    plan_id=matched_plan.id if matched_plan else None,
                    subscription_status="active",
                    commercial_state="active",
                    reason="invoice_payment_succeeded",
                    clear_grace_end_at=True,
                )
                action_taken = "active"

        updated = await ensure_billing_event(
            session,
            provider=event.provider,
            external_event_id=event.event_id,
            event_type=event.event_type,
            raw_payload=payload,
            tenant_id=subscription.tenant_id if subscription else tenant_id,
            subscription_id=subscription.id if subscription else (str(local_subscription_id) if local_subscription_id else None),
            processing_status="processed",
            action_taken=action_taken,
        )
        return updated

    except Exception as exc:
        failed = await ensure_billing_event(
            session,
            provider=event.provider,
            external_event_id=event.event_id,
            event_type=event.event_type,
            raw_payload=payload,
            tenant_id=subscription.tenant_id if subscription else tenant_id,
            subscription_id=subscription.id if subscription else (str(local_subscription_id) if local_subscription_id else None),
            processing_status="failed",
            action_taken="error",
            error_message=str(exc),
        )
        return failed


def _extract_timestamp(payload: dict[str, Any], key: str) -> datetime | None:
    try:
        value = payload.get("data", {}).get("object", {}).get(key)
        if value is None:
            return None
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except Exception:
        return None


@dataclass(slots=True)
class CommercialPaymentMethodDetails:
    id: str
    tenant_id: str
    provider_customer_id: str
    provider_payment_method_id: str
    provider_type: str
    card_brand: str | None
    card_last4: str | None
    card_exp_month: int | None
    card_exp_year: int | None
    billing_email: str | None
    billing_name: str | None
    is_default: bool
    is_active: bool
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


def _row_to_payment_method(row: dict[str, Any]) -> CommercialPaymentMethodDetails:
    return CommercialPaymentMethodDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        provider_customer_id=str(row["provider_customer_id"]),
        provider_payment_method_id=str(row["provider_payment_method_id"]),
        provider_type=str(row["provider_type"]),
        card_brand=row["card_brand"],
        card_last4=row["card_last4"],
        card_exp_month=row["card_exp_month"],
        card_exp_year=row["card_exp_year"],
        billing_email=row["billing_email"],
        billing_name=row["billing_name"],
        is_default=bool(row["is_default"]),
        is_active=bool(row["is_active"]),
        metadata=dict(row["metadata"] or {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_payment_methods(
    session: AsyncSession,
    *,
    tenant_id: str,
    include_inactive: bool = False,
) -> list[CommercialPaymentMethodDetails]:
    query = """
        select
            id,
            tenant_id,
            provider_customer_id,
            provider_payment_method_id,
            provider_type,
            card_brand,
            card_last4,
            card_exp_month,
            card_exp_year,
            billing_email,
            billing_name,
            is_default,
            is_active,
            metadata,
            created_at,
            updated_at
        from public.commercial_payment_methods
        where tenant_id = cast(:tenant_id as varchar)
    """
    params: dict[str, Any] = {"tenant_id": tenant_id}
    if not include_inactive:
        query += " and is_active = true"
    query += " order by is_default desc, created_at desc"
    result = await session.execute(text(query), params)
    return [_row_to_payment_method(dict(row)) for row in result.mappings().all()]


async def get_default_payment_method(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> CommercialPaymentMethodDetails | None:
    methods = await list_payment_methods(session, tenant_id=tenant_id, include_inactive=False)
    for method in methods:
        if method.is_default and method.is_active:
            return method
    return methods[0] if methods else None


async def get_payment_method_by_id(
    session: AsyncSession,
    *,
    payment_method_id: str,
    tenant_id: str,
) -> CommercialPaymentMethodDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                provider_customer_id,
                provider_payment_method_id,
                provider_type,
                card_brand,
                card_last4,
                card_exp_month,
                card_exp_year,
                billing_email,
                billing_name,
                is_default,
                is_active,
                metadata,
                created_at,
                updated_at
            from public.commercial_payment_methods
            where id = cast(:id as varchar)
              and tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {"id": payment_method_id, "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    return _row_to_payment_method(dict(row)) if row else None


async def create_payment_method(
    session: AsyncSession,
    *,
    tenant_id: str,
    provider_customer_id: str,
    provider_payment_method_id: str,
    provider_type: str = "stripe",
    card_brand: str | None = None,
    card_last4: str | None = None,
    card_exp_month: int | None = None,
    card_exp_year: int | None = None,
    billing_email: str | None = None,
    billing_name: str | None = None,
    is_default: bool = False,
    metadata: dict[str, Any] | None = None,
) -> CommercialPaymentMethodDetails:
    if is_default:
        await session.execute(
            text(
                """
                update public.commercial_payment_methods
                set is_default = false, updated_at = now()
                where tenant_id = cast(:tenant_id as varchar)
                  and provider_customer_id = cast(:provider_customer_id as varchar)
                """
            ),
            {"tenant_id": tenant_id, "provider_customer_id": provider_customer_id},
        )

    result = await session.execute(
        text(
            """
            insert into public.commercial_payment_methods (
                id,
                tenant_id,
                provider_customer_id,
                provider_payment_method_id,
                provider_type,
                card_brand,
                card_last4,
                card_exp_month,
                card_exp_year,
                billing_email,
                billing_name,
                is_default,
                is_active,
                metadata
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:provider_customer_id as varchar),
                cast(:provider_payment_method_id as varchar),
                cast(:provider_type as varchar),
                cast(:card_brand as varchar),
                cast(:card_last4 as varchar),
                cast(:card_exp_month as integer),
                cast(:card_exp_year as integer),
                cast(:billing_email as varchar),
                cast(:billing_name as varchar),
                :is_default,
                true,
                cast(:metadata as jsonb)
            )
            on conflict (provider_payment_method_id) do update
              set tenant_id = excluded.tenant_id,
                  provider_customer_id = excluded.provider_customer_id,
                  provider_type = excluded.provider_type,
                  card_brand = excluded.card_brand,
                  card_last4 = excluded.card_last4,
                  card_exp_month = excluded.card_exp_month,
                  card_exp_year = excluded.card_exp_year,
                  billing_email = excluded.billing_email,
                  billing_name = excluded.billing_name,
                  is_default = excluded.is_default,
                  is_active = true,
                  metadata = excluded.metadata,
                  updated_at = now()
            returning
                id,
                tenant_id,
                provider_customer_id,
                provider_payment_method_id,
                provider_type,
                card_brand,
                card_last4,
                card_exp_month,
                card_exp_year,
                billing_email,
                billing_name,
                is_default,
                is_active,
                metadata,
                created_at,
                updated_at
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "provider_customer_id": provider_customer_id,
            "provider_payment_method_id": provider_payment_method_id,
            "provider_type": provider_type,
            "card_brand": card_brand,
            "card_last4": card_last4,
            "card_exp_month": card_exp_month,
            "card_exp_year": card_exp_year,
            "billing_email": billing_email,
            "billing_name": billing_name,
            "is_default": is_default,
            "metadata": json.dumps(metadata or {}),
        },
    )
    return _row_to_payment_method(dict(result.mappings().one()))


async def update_payment_method(
    session: AsyncSession,
    *,
    payment_method_id: str,
    tenant_id: str,
    is_default: bool | None = None,
    is_active: bool | None = None,
    billing_email: str | None = None,
    billing_name: str | None = None,
) -> CommercialPaymentMethodDetails:
    existing = await get_payment_method_by_id(session, payment_method_id=payment_method_id, tenant_id=tenant_id)
    if not existing:
        raise ValueError(f"Payment method does not exist: {payment_method_id}")

    if is_default:
        await session.execute(
            text(
                """
                update public.commercial_payment_methods
                set is_default = false, updated_at = now()
                where tenant_id = cast(:tenant_id as varchar)
                  and provider_customer_id = cast(:provider_customer_id as varchar)
                  and id != cast(:payment_method_id as varchar)
                """
            ),
            {
                "tenant_id": tenant_id,
                "provider_customer_id": existing.provider_customer_id,
                "payment_method_id": payment_method_id,
            },
        )

    result = await session.execute(
        text(
            """
            update public.commercial_payment_methods
            set is_default = coalesce(:is_default, is_default),
                is_active = coalesce(:is_active, is_active),
                billing_email = coalesce(cast(:billing_email as varchar), billing_email),
                billing_name = coalesce(cast(:billing_name as varchar), billing_name),
                updated_at = now()
            where id = cast(:payment_method_id as varchar)
              and tenant_id = cast(:tenant_id as varchar)
            returning
                id,
                tenant_id,
                provider_customer_id,
                provider_payment_method_id,
                provider_type,
                card_brand,
                card_last4,
                card_exp_month,
                card_exp_year,
                billing_email,
                billing_name,
                is_default,
                is_active,
                metadata,
                created_at,
                updated_at
            """
        ),
        {
            "payment_method_id": payment_method_id,
            "tenant_id": tenant_id,
            "is_default": is_default,
            "is_active": is_active,
            "billing_email": billing_email,
            "billing_name": billing_name,
        },
    )
    return _row_to_payment_method(dict(result.mappings().one()))


async def set_default_payment_method(
    session: AsyncSession,
    *,
    payment_method_id: str,
    tenant_id: str,
) -> CommercialPaymentMethodDetails:
    existing = await get_payment_method_by_id(session, payment_method_id=payment_method_id, tenant_id=tenant_id)
    if not existing:
        raise ValueError(f"Payment method does not exist: {payment_method_id}")

    await session.execute(
        text(
            """
            update public.commercial_payment_methods
            set is_default = false, updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and provider_customer_id = cast(:provider_customer_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "provider_customer_id": existing.provider_customer_id},
    )

    result = await session.execute(
        text(
            """
            update public.commercial_payment_methods
            set is_default = true, updated_at = now()
            where id = cast(:payment_method_id as varchar)
              and tenant_id = cast(:tenant_id as varchar)
            returning
                id,
                tenant_id,
                provider_customer_id,
                provider_payment_method_id,
                provider_type,
                card_brand,
                card_last4,
                card_exp_month,
                card_exp_year,
                billing_email,
                billing_name,
                is_default,
                is_active,
                metadata,
                created_at,
                updated_at
            """
        ),
        {"payment_method_id": payment_method_id, "tenant_id": tenant_id},
    )
    return _row_to_payment_method(dict(result.mappings().one()))


async def create_payment_method_checkout_session(
    session: AsyncSession,
    *,
    tenant_id: str,
    customer_email: str | None = None,
    customer_name: str | None = None,
) -> CommercialCheckoutSessionDetails:
    subscription = await get_subscription_by_tenant(session, tenant_id=tenant_id)
    if not subscription:
        raise ValueError(f"No subscription found for tenant: {tenant_id}")

    provider_client = await _get_tenant_provider_client(
        session,
        tenant_id=tenant_id,
        provider=subscription.provider,
    )

    provider_customer_id = subscription.provider_customer_id
    if not provider_customer_id:
        provider_customer_id = await provider_client.create_customer(
            email=customer_email or f"billing+{tenant_id}@supacrm.local",
            metadata={
                "tenant_id": tenant_id,
                "subscription_id": subscription.id,
                "customer_name": customer_name or "",
            },
        )
        subscription = await change_subscription_state(
            session,
            subscription_id=subscription.id,
            subscription_status=subscription.subscription_status,
            commercial_state=subscription.commercial_state,
            provider_customer_id=provider_customer_id,
            reason=subscription.state_reason,
        )

    success_url, cancel_url = _build_checkout_urls(tenant_id=tenant_id, mode="setup")
    session_result = await provider_client.create_checkout_session(
        mode="setup",
        success_url=success_url,
        cancel_url=cancel_url,
        customer_id=provider_customer_id,
        customer_email=customer_email,
        metadata={
            "tenant_id": tenant_id,
            "subscription_id": subscription.id,
            "plan_code": subscription.plan_code,
        },
    )

    return CommercialCheckoutSessionDetails(
        provider=session_result.provider,
        session_id=session_result.session_id,
        url=session_result.url,
        mode=session_result.mode,
        provider_customer_id=session_result.provider_customer_id or provider_customer_id,
        provider_subscription_id=session_result.provider_subscription_id,
    )


async def convert_trial_to_paid(
    session: AsyncSession,
    *,
    tenant_id: str,
    payment_method_id: str | None = None,
    plan_code: str | None = None,
) -> CommercialSubscriptionDetails:
    subscription = await get_subscription_by_tenant(session, tenant_id=tenant_id)
    if not subscription:
        raise ValueError(f"No subscription found for tenant: {tenant_id}")

    if subscription.commercial_state != "trial" and subscription.subscription_status not in {"trialing", "trial"}:
        raise ValueError(f"Subscription is not in trial state: {subscription.commercial_state}")

    plan = None
    if plan_code:
        plan = await get_plan_by_code(session, code=plan_code)
        if not plan:
            raise ValueError(f"Commercial plan does not exist: {plan_code}")
    else:
        plan = await get_plan_by_id(session, plan_id=subscription.plan_id)

    if not plan:
        raise ValueError("Could not determine plan for conversion")

    if not plan.provider_price_id:
        raise ValueError(f"Commercial plan is missing provider_price_id: {plan.code}")

    provider_client = await _get_tenant_provider_client(
        session,
        tenant_id=tenant_id,
        provider=subscription.provider,
    )

    selected_payment_method = None
    if payment_method_id:
        selected_payment_method = await get_payment_method_by_id(session, payment_method_id=payment_method_id, tenant_id=tenant_id)
        if not selected_payment_method:
            raise ValueError(f"Payment method does not exist: {payment_method_id}")
    else:
        selected_payment_method = await get_default_payment_method(session, tenant_id=tenant_id)

    if not selected_payment_method:
        raise ValueError("A default payment method is required before converting trial to paid")

    if subscription.provider_customer_id:
        await provider_client.attach_payment_method(
            customer_id=subscription.provider_customer_id,
            payment_method_id=selected_payment_method.provider_payment_method_id,
        )
        await provider_client.set_default_payment_method(
            customer_id=subscription.provider_customer_id,
            payment_method_id=selected_payment_method.provider_payment_method_id,
        )

    if subscription.provider_subscription_id:
        subscription_result = await provider_client.update_subscription(
            subscription_id=subscription.provider_subscription_id,
            price_id=plan.provider_price_id,
            trial_end_at_now=True,
        )
        return await change_subscription_state(
            session,
            subscription_id=subscription.id,
            plan_id=subscription.plan_id,
            subscription_status=subscription_result.status,
            commercial_state="trial",
            reason="awaiting_stripe_invoice_confirmation",
            provider_customer_id=subscription_result.provider_customer_id or subscription.provider_customer_id,
            provider_subscription_id=subscription_result.provider_subscription_id or subscription.provider_subscription_id,
            trial_end_at=subscription_result.trial_end_at,
            current_period_start_at=subscription_result.current_period_start_at,
            current_period_end_at=subscription_result.current_period_end_at,
        )

    restarted = await bootstrap_tenant_subscription(
        session,
        tenant_id=tenant_id,
        plan_code=plan.code,
        provider=subscription.provider,
        start_trial=False,
    )
    return restarted


async def change_subscription_plan(
    session: AsyncSession,
    *,
    tenant_id: str,
    new_plan_code: str,
    prorate: bool = True,
) -> CommercialSubscriptionDetails:
    subscription = await get_subscription_by_tenant(session, tenant_id=tenant_id)
    if not subscription:
        raise ValueError(f"No subscription found for tenant: {tenant_id}")

    new_plan = await get_plan_by_code(session, code=new_plan_code)
    if not new_plan:
        raise ValueError(f"Commercial plan does not exist: {new_plan_code}")
    if not new_plan.is_active:
        raise ValueError(f"Commercial plan is inactive: {new_plan_code}")

    if not new_plan.provider_price_id:
        raise ValueError(f"Commercial plan is missing provider_price_id: {new_plan.code}")

    if not subscription.provider_subscription_id:
        raise ValueError("Subscription does not exist in Stripe yet")

    provider_client = await _get_tenant_provider_client(
        session,
        tenant_id=tenant_id,
        provider=subscription.provider,
    )

    subscription_result = await provider_client.update_subscription(
        subscription_id=subscription.provider_subscription_id,
        price_id=new_plan.provider_price_id,
        prorate=prorate,
    )

    return await change_subscription_state(
        session,
        subscription_id=subscription.id,
        subscription_status=subscription_result.status,
        commercial_state=subscription.commercial_state,
        reason="awaiting_stripe_plan_change_confirmation",
        provider_customer_id=subscription_result.provider_customer_id,
        provider_subscription_id=subscription_result.provider_subscription_id,
        current_period_start_at=subscription_result.current_period_start_at,
        current_period_end_at=subscription_result.current_period_end_at,
        cancel_at_period_end=subscription_result.cancel_at_period_end,
    )


async def request_subscription_cancellation(
    session: AsyncSession,
    *,
    tenant_id: str,
    cancel_at_period_end: bool = True,
) -> CommercialSubscriptionDetails:
    subscription = await get_subscription_by_tenant(session, tenant_id=tenant_id)
    if not subscription:
        raise ValueError(f"No subscription found for tenant: {tenant_id}")
    if not subscription.provider_subscription_id:
        raise ValueError("Subscription does not exist in Stripe yet")

    provider_client = await _get_tenant_provider_client(
        session,
        tenant_id=tenant_id,
        provider=subscription.provider,
    )
    provider_result = await provider_client.cancel_subscription(
        subscription_id=subscription.provider_subscription_id,
        cancel_at_period_end=cancel_at_period_end,
    )
    return await change_subscription_state(
        session,
        subscription_id=subscription.id,
        subscription_status=provider_result.status,
        commercial_state=subscription.commercial_state,
        reason="awaiting_stripe_cancellation_confirmation",
        provider_customer_id=provider_result.provider_customer_id or subscription.provider_customer_id,
        provider_subscription_id=provider_result.provider_subscription_id or subscription.provider_subscription_id,
        trial_end_at=provider_result.trial_end_at,
        current_period_start_at=provider_result.current_period_start_at,
        current_period_end_at=provider_result.current_period_end_at,
        cancel_at_period_end=provider_result.cancel_at_period_end,
    )

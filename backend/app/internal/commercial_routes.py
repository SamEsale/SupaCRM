from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.commercial.schemas import CommercialPlanCreateRequest, CommercialPlanOut, CommercialPlanUpdateRequest, CommercialSubscriptionOut, CommercialSubscriptionStateUpdateRequest
from app.commercial.service import (
    bootstrap_tenant_subscription,
    cancel_subscription,
    create_plan,
    ensure_plan_catalog,
    list_plans,
    summarize_plan_features,
    suspend_subscription,
    update_plan,
)
from app.core.config import settings
from app.db_admin import get_admin_session

router = APIRouter(prefix="/internal/bootstrap/commercial", tags=["internal-commercial"])


def require_bootstrap_key(x_bootstrap_key: str | None = Header(default=None)) -> None:
    if not x_bootstrap_key or x_bootstrap_key != settings.BOOTSTRAP_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bootstrap key")


def _to_plan_out(plan) -> CommercialPlanOut:
    return CommercialPlanOut(
        **asdict(plan),
        plan_code=plan.code,
        features_summary=summarize_plan_features(plan.features),
    )


@router.get("/plans", dependencies=[Depends(require_bootstrap_key)])
async def list_plans_internal(admin_session: AsyncSession = Depends(get_admin_session)) -> list[CommercialPlanOut]:
    async with admin_session.begin():
        await ensure_plan_catalog(admin_session)
        plans = await list_plans(admin_session, include_inactive=True)
    return [_to_plan_out(plan) for plan in plans]


@router.post("/plans", dependencies=[Depends(require_bootstrap_key)])
async def create_plan_internal(
    payload: CommercialPlanCreateRequest,
    admin_session: AsyncSession = Depends(get_admin_session),
) -> CommercialPlanOut:
    async with admin_session.begin():
        plan = await create_plan(
            admin_session,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            provider=payload.provider,
            provider_price_id=payload.provider_price_id,
            billing_interval=payload.billing_interval,
            price_amount=payload.price_amount,
            currency=payload.currency,
            trial_days=payload.trial_days,
            grace_days=payload.grace_days,
            is_active=payload.is_active,
            features=payload.features,
        )
    return _to_plan_out(plan)


@router.patch("/plans/{plan_code}", dependencies=[Depends(require_bootstrap_key)])
async def update_plan_internal(
    plan_code: str,
    payload: CommercialPlanUpdateRequest,
    admin_session: AsyncSession = Depends(get_admin_session),
) -> CommercialPlanOut:
    async with admin_session.begin():
        plan = await update_plan(
            admin_session,
            code=plan_code,
            name=payload.name,
            description=payload.description,
            provider=payload.provider,
            provider_price_id=payload.provider_price_id,
            billing_interval=payload.billing_interval,
            price_amount=payload.price_amount,
            currency=payload.currency,
            trial_days=payload.trial_days,
            grace_days=payload.grace_days,
            is_active=payload.is_active,
            features=payload.features,
        )
    return _to_plan_out(plan)


@router.post("/tenants/{tenant_id}/trial", dependencies=[Depends(require_bootstrap_key)])
async def bootstrap_tenant_trial_internal(
    tenant_id: str,
    plan_code: str = "starter",
    admin_session: AsyncSession = Depends(get_admin_session),
) -> CommercialSubscriptionOut:
    subscription = await bootstrap_tenant_subscription(
        admin_session,
        tenant_id=tenant_id,
        plan_code=plan_code,
        provider="stripe",
    )
    return CommercialSubscriptionOut(**asdict(subscription))


@router.post("/subscriptions/{subscription_id}/suspend", dependencies=[Depends(require_bootstrap_key)])
async def suspend_subscription_internal(
    subscription_id: str,
    payload: CommercialSubscriptionStateUpdateRequest,
    admin_session: AsyncSession = Depends(get_admin_session),
) -> CommercialSubscriptionOut:
    subscription = await suspend_subscription(admin_session, subscription_id=subscription_id, reason=payload.reason)
    return CommercialSubscriptionOut(**asdict(subscription))


@router.post("/subscriptions/{subscription_id}/cancel", dependencies=[Depends(require_bootstrap_key)])
async def cancel_subscription_internal(
    subscription_id: str,
    payload: CommercialSubscriptionStateUpdateRequest,
    admin_session: AsyncSession = Depends(get_admin_session),
) -> CommercialSubscriptionOut:
    subscription = await cancel_subscription(admin_session, subscription_id=subscription_id, reason=payload.reason)
    return CommercialSubscriptionOut(**asdict(subscription))

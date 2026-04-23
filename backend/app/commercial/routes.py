from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.commercial.deps import get_commercial_db, get_commercial_principal
from app.commercial.providers import get_commercial_provider
from app.commercial.schemas import (
    CommercialBillingEventOut,
    CommercialBillingEventSummaryOut,
    CommercialBillingCycleSummaryOut,
    CommercialCheckoutSessionOut,
    CommercialCheckoutSessionRequest,
    CommercialLifecycleResponse,
    CommercialPaymentMethodCreateRequest,
    CommercialPaymentMethodListResponse,
    CommercialPaymentMethodOut,
    CommercialPaymentMethodUpdateRequest,
    CommercialPlanCreateRequest,
    CommercialPlanOut,
    CommercialPlanUpdateRequest,
    CommercialSubscriptionChangePlanRequest,
    CommercialSubscriptionCreateRequest,
    CommercialSubscriptionOut,
    CommercialSubscriptionSummaryOut,
    CommercialSubscriptionStateUpdateRequest,
    CommercialTrialConversionRequest,
    TenantCommercialStatusOut,
)
from app.commercial.service import (
    bootstrap_tenant_subscription,
    cancel_subscription,
    change_subscription_plan,
    change_subscription_state,
    create_payment_method_checkout_session,
    convert_trial_to_paid,
    create_plan,
    create_payment_method,
    ensure_plan_catalog,
    get_payment_method_by_id,
    get_tenant_commercial_status,
    get_subscription_summary_by_tenant,
    get_subscription_by_tenant,
    list_payment_methods,
    list_plans,
    mark_subscription_grace,
    process_provider_event,
    reactivate_subscription,
    request_subscription_cancellation,
    set_default_payment_method,
    set_subscription_past_due,
    summarize_plan_features,
    suspend_subscription,
    update_payment_method,
    update_plan,
)
from app.rbac.permissions import PERMISSION_BILLING_ACCESS
from app.commercial.deps import require_commercial_permission
from app.db_admin import get_admin_session

router = APIRouter(prefix="/commercial", tags=["commercial"])
webhook_router = APIRouter(prefix="/commercial/webhooks", tags=["commercial-webhooks"])


def _raise_for_commercial_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if detail.startswith("Commercial plan does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    if detail.startswith("Commercial plan is inactive"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    if detail.startswith("Subscription does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    if (
        detail.startswith("Payment provider is not enabled for tenant")
        or detail.startswith("Payment provider is not fully configured for tenant")
        or detail.startswith("Commercial subscription automation is not implemented for provider")
        or detail.startswith("Unsupported commercial provider")
        or detail.startswith("Payment gateway settings require the latest database migration")
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _to_plan_out(plan) -> CommercialPlanOut:
    return CommercialPlanOut(
        **asdict(plan),
        plan_code=plan.code,
        features_summary=summarize_plan_features(plan.features),
    )


def _to_subscription_out(subscription) -> CommercialSubscriptionOut:
    return CommercialSubscriptionOut(**asdict(subscription))


@router.get("/catalog", response_model=list[CommercialPlanOut])
async def list_public_commercial_catalog_route(
    db: AsyncSession = Depends(get_admin_session),
) -> list[CommercialPlanOut]:
    async with db.begin():
        await ensure_plan_catalog(db)
        plans = await list_plans(db, include_inactive=False)
    return [_to_plan_out(plan) for plan in plans]


@router.get("/plans", response_model=list[CommercialPlanOut])
async def list_commercial_plans_route(
    _: bool = Depends(require_commercial_permission(PERMISSION_BILLING_ACCESS)),
    db: AsyncSession = Depends(get_admin_session),
) -> list[CommercialPlanOut]:
    async with db.begin():
        await ensure_plan_catalog(db)
        plans = await list_plans(db, include_inactive=True)
    return [_to_plan_out(plan) for plan in plans]


@router.get("/status", response_model=TenantCommercialStatusOut)
async def get_current_tenant_commercial_status_route(
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> TenantCommercialStatusOut:
    status_model = await get_tenant_commercial_status(
        db,
        tenant_id=str(principal["tenant_id"]),
    )
    return TenantCommercialStatusOut(
        current_plan=_to_plan_out(status_model.current_plan) if status_model.current_plan else None,
        subscription=_to_subscription_out(status_model.subscription) if status_model.subscription else None,
        subscription_status=status_model.subscription_status,
        trial_status=status_model.trial_status,
        next_billing_at=status_model.next_billing_at,
        renewal_at=status_model.renewal_at,
        provider=status_model.provider,
        provider_name=status_model.provider_name,
        provider_customer_id=status_model.provider_customer_id,
        provider_subscription_id=status_model.provider_subscription_id,
        commercially_active=status_model.commercially_active,
    )


@router.post("/plans", response_model=CommercialPlanOut)
async def create_commercial_plan_route(
    payload: CommercialPlanCreateRequest,
    _: bool = Depends(require_commercial_permission(PERMISSION_BILLING_ACCESS)),
    db: AsyncSession = Depends(get_admin_session),
) -> CommercialPlanOut:
    try:
        async with db.begin():
            plan = await create_plan(
                db,
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
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc
    return _to_plan_out(plan)


@router.patch("/plans/{plan_code}", response_model=CommercialPlanOut)
async def update_commercial_plan_route(
    plan_code: str,
    payload: CommercialPlanUpdateRequest,
    _: bool = Depends(require_commercial_permission(PERMISSION_BILLING_ACCESS)),
    db: AsyncSession = Depends(get_admin_session),
) -> CommercialPlanOut:
    try:
        async with db.begin():
            plan = await update_plan(
                db,
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
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc
    return _to_plan_out(plan)


@router.get("/subscription", response_model=CommercialSubscriptionOut)
async def get_current_subscription_route(
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    subscription = await get_subscription_by_tenant(db, tenant_id=str(principal["tenant_id"]))
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return _to_subscription_out(subscription)


@router.get("/subscription/summary", response_model=CommercialSubscriptionSummaryOut)
async def get_current_subscription_summary_route(
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionSummaryOut:
    summary = await get_subscription_summary_by_tenant(
        db,
        tenant_id=str(principal["tenant_id"]),
    )
    return CommercialSubscriptionSummaryOut(
        subscription=_to_subscription_out(summary.subscription) if summary.subscription else None,
        recent_billing_cycles=[
            CommercialBillingCycleSummaryOut(
                id=cycle.id,
                cycle_number=cycle.cycle_number,
                period_start_at=cycle.period_start_at,
                period_end_at=cycle.period_end_at,
                due_at=cycle.due_at,
                amount=cycle.amount,
                currency=cycle.currency,
                status=cycle.status,
                invoice_id=cycle.invoice_id,
                created_at=cycle.created_at,
            )
            for cycle in summary.recent_billing_cycles
        ],
        recent_billing_events=[
            CommercialBillingEventSummaryOut(
                id=event.id,
                provider=event.provider,
                external_event_id=event.external_event_id,
                event_type=event.event_type,
                processing_status=event.processing_status,
                action_taken=event.action_taken,
                error_message=event.error_message,
                processed_at=event.processed_at,
                created_at=event.created_at,
            )
            for event in summary.recent_billing_events
        ],
    )


@router.post("/subscription", response_model=CommercialSubscriptionOut)
async def start_subscription_route(
    payload: CommercialSubscriptionCreateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    try:
        existing = await get_subscription_by_tenant(db, tenant_id=str(principal["tenant_id"]))
        if not payload.start_trial and existing and existing.provider_subscription_id and existing.subscription_status in {"trialing", "trial"}:
            subscription = await convert_trial_to_paid(
                db,
                tenant_id=str(principal["tenant_id"]),
                plan_code=payload.plan_code,
            )
        else:
            subscription = await bootstrap_tenant_subscription(
                db,
                tenant_id=str(principal["tenant_id"]),
                plan_code=payload.plan_code,
                provider=payload.provider,
                start_trial=payload.start_trial,
                customer_email=payload.customer_email,
                customer_name=payload.customer_name,
                metadata={"request_id": getattr(request.state, "request_id", None)},
            )
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc

    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.start",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=subscription.id,
        status_code=status.HTTP_200_OK,
        message="Commercial subscription started",
        meta={
            "plan_code": payload.plan_code,
            "state": subscription.commercial_state,
            "subscription_status": subscription.subscription_status,
        },
    )
    return _to_subscription_out(subscription)


@router.post("/subscription/{subscription_id}/activate", response_model=CommercialSubscriptionOut)
async def activate_subscription_route(
    subscription_id: str,
    payload: CommercialSubscriptionStateUpdateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    try:
        subscription = await change_subscription_state(db, subscription_id=subscription_id, commercial_state="active", reason=payload.reason)
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc
    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.activate",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=subscription.id,
        status_code=status.HTTP_200_OK,
        message="Commercial subscription activated",
        meta={"state": subscription.commercial_state, "reason": payload.reason},
    )
    return _to_subscription_out(subscription)


@router.post("/subscription/{subscription_id}/past-due", response_model=CommercialSubscriptionOut)
async def mark_subscription_past_due_route(
    subscription_id: str,
    payload: CommercialSubscriptionStateUpdateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    try:
        subscription = await set_subscription_past_due(db, subscription_id=subscription_id, reason=payload.reason)
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc
    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.past_due",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=subscription.id,
        status_code=status.HTTP_200_OK,
        message="Commercial subscription marked past due",
        meta={"state": subscription.commercial_state, "reason": payload.reason},
    )
    return _to_subscription_out(subscription)


@router.post("/subscription/{subscription_id}/grace", response_model=CommercialSubscriptionOut)
async def mark_subscription_grace_route(
    subscription_id: str,
    payload: CommercialSubscriptionStateUpdateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    try:
        subscription = await mark_subscription_grace(db, subscription_id=subscription_id, reason=payload.reason)
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc
    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.grace",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=subscription.id,
        status_code=status.HTTP_200_OK,
        message="Commercial subscription entered grace period",
        meta={"state": subscription.commercial_state, "reason": payload.reason},
    )
    return _to_subscription_out(subscription)


@router.post("/subscription/{subscription_id}/suspend", response_model=CommercialSubscriptionOut)
async def suspend_subscription_route(
    subscription_id: str,
    payload: CommercialSubscriptionStateUpdateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    try:
        subscription = await suspend_subscription(db, subscription_id=subscription_id, reason=payload.reason)
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc
    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.suspend",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=subscription.id,
        status_code=status.HTTP_200_OK,
        message="Commercial subscription suspended",
        meta={"state": subscription.commercial_state, "reason": payload.reason},
    )
    return _to_subscription_out(subscription)


@router.post("/subscription/{subscription_id}/reactivate", response_model=CommercialSubscriptionOut)
async def reactivate_subscription_route(
    subscription_id: str,
    payload: CommercialSubscriptionStateUpdateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    try:
        subscription = await reactivate_subscription(db, subscription_id=subscription_id, reason=payload.reason)
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc
    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.reactivate",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=subscription.id,
        status_code=status.HTTP_200_OK,
        message="Commercial subscription reactivated",
        meta={"state": subscription.commercial_state, "reason": payload.reason},
    )
    return _to_subscription_out(subscription)


@router.post("/subscription/{subscription_id}/cancel", response_model=CommercialSubscriptionOut)
async def cancel_subscription_route(
    subscription_id: str,
    payload: CommercialSubscriptionStateUpdateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    try:
        current = await get_subscription_by_tenant(db, tenant_id=str(principal["tenant_id"]))
        if not current or current.id != subscription_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        subscription = await request_subscription_cancellation(
            db,
            tenant_id=str(principal["tenant_id"]),
            cancel_at_period_end=True,
        )
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc
    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.cancel",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=subscription.id,
        status_code=status.HTTP_200_OK,
        message="Commercial subscription cancellation requested",
        meta={
            "state": subscription.commercial_state,
            "subscription_status": subscription.subscription_status,
            "reason": payload.reason,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        },
    )
    return _to_subscription_out(subscription)


@webhook_router.post("/stripe")
async def stripe_webhook_route(
    request: Request,
    db: AsyncSession = Depends(get_admin_session),
) -> CommercialLifecycleResponse:
    body = await request.body()
    provider = get_commercial_provider("stripe")
    headers = {key.lower(): value for key, value in request.headers.items()}
    try:
        is_valid = await provider.verify_webhook_signature(payload=body, headers=headers)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")
    try:
        event = await provider.parse_webhook_event(payload=body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    billing_event = await process_provider_event(db, event)
    await db.commit()
    if billing_event.processing_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stripe webhook processing failed for {billing_event.external_event_id}",
        )
    return CommercialLifecycleResponse(
        billing_event=CommercialBillingEventOut(**asdict(billing_event)),
    )


@router.get("/payment-methods", response_model=CommercialPaymentMethodListResponse)
async def list_payment_methods_route(
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
    include_inactive: bool = Query(default=False),
) -> CommercialPaymentMethodListResponse:
    methods = await list_payment_methods(
        db,
        tenant_id=str(principal["tenant_id"]),
        include_inactive=include_inactive,
    )
    return CommercialPaymentMethodListResponse(
        items=[
            CommercialPaymentMethodOut(**asdict(m))
            for m in methods
        ],
        total=len(methods),
    )


@router.post("/payment-methods/checkout-session", response_model=CommercialCheckoutSessionOut)
async def create_payment_method_checkout_session_route(
    payload: CommercialCheckoutSessionRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialCheckoutSessionOut:
    try:
        checkout_session = await create_payment_method_checkout_session(
            db,
            tenant_id=str(principal["tenant_id"]),
            customer_email=payload.customer_email,
            customer_name=payload.customer_name,
        )
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc

    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.payment_method.checkout_session.create",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="payment_method_checkout_session",
        resource_id=checkout_session.session_id,
        status_code=status.HTTP_200_OK,
        message="Stripe setup checkout session created",
        meta={"provider": checkout_session.provider, "mode": checkout_session.mode},
    )

    return CommercialCheckoutSessionOut(**asdict(checkout_session))


@router.post("/payment-methods", response_model=CommercialPaymentMethodOut, status_code=status.HTTP_201_CREATED)
async def create_payment_method_route(
    payload: CommercialPaymentMethodCreateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialPaymentMethodOut:
    subscription = await get_subscription_by_tenant(db, tenant_id=str(principal["tenant_id"]))
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found for tenant")
    if not subscription.provider_customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No provider customer ID found")

    provider = get_commercial_provider(subscription.provider)
    pm_data = await provider.get_payment_method(payment_method_id=payload.provider_payment_method_id)

    card_details = pm_data.get("card", {})
    billing_details = pm_data.get("billing_details", {})

    payment_method = await create_payment_method(
        db,
        tenant_id=str(principal["tenant_id"]),
        provider_customer_id=subscription.provider_customer_id,
        provider_payment_method_id=payload.provider_payment_method_id,
        provider_type=subscription.provider,
        card_brand=card_details.get("brand"),
        card_last4=card_details.get("last4"),
        card_exp_month=card_details.get("exp_month"),
        card_exp_year=card_details.get("exp_year"),
        billing_email=billing_details.get("email") or payload.billing_email,
        billing_name=billing_details.get("name") or payload.billing_name,
        is_default=True,
        metadata={"provider_raw": pm_data},
    )

    await provider.set_default_payment_method(
        customer_id=subscription.provider_customer_id,
        payment_method_id=payload.provider_payment_method_id,
    )

    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.payment_method.create",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="payment_method",
        resource_id=payment_method.id,
        status_code=status.HTTP_201_CREATED,
        message="Payment method added",
        meta={"provider_payment_method_id": payload.provider_payment_method_id},
    )

    return CommercialPaymentMethodOut(**asdict(payment_method))


@router.get("/payment-methods/{payment_method_id}", response_model=CommercialPaymentMethodOut)
async def get_payment_method_route(
    payment_method_id: str,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialPaymentMethodOut:
    method = await get_payment_method_by_id(
        db,
        payment_method_id=payment_method_id,
        tenant_id=str(principal["tenant_id"]),
    )
    if not method:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
    return CommercialPaymentMethodOut(**asdict(method))


@router.patch("/payment-methods/{payment_method_id}", response_model=CommercialPaymentMethodOut)
async def update_payment_method_route(
    payment_method_id: str,
    payload: CommercialPaymentMethodUpdateRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialPaymentMethodOut:
    method = await update_payment_method(
        db,
        payment_method_id=payment_method_id,
        tenant_id=str(principal["tenant_id"]),
        is_default=payload.is_default,
        is_active=payload.is_active,
        billing_email=payload.billing_email,
        billing_name=payload.billing_name,
    )

    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.payment_method.update",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="payment_method",
        resource_id=method.id,
        status_code=status.HTTP_200_OK,
        message="Payment method updated",
        meta={"is_default": method.is_default, "is_active": method.is_active},
    )

    return CommercialPaymentMethodOut(**asdict(method))


@router.post("/payment-methods/{payment_method_id}/set-default", response_model=CommercialPaymentMethodOut)
async def set_default_payment_method_route(
    payment_method_id: str,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialPaymentMethodOut:
    method = await set_default_payment_method(
        db,
        payment_method_id=payment_method_id,
        tenant_id=str(principal["tenant_id"]),
    )

    subscription = await get_subscription_by_tenant(db, tenant_id=str(principal["tenant_id"]))
    if subscription and subscription.provider_customer_id:
        provider = get_commercial_provider(subscription.provider)
        await provider.set_default_payment_method(
            customer_id=subscription.provider_customer_id,
            payment_method_id=method.provider_payment_method_id,
        )

    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.payment_method.set_default",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="payment_method",
        resource_id=method.id,
        status_code=status.HTTP_200_OK,
        message="Default payment method set",
        meta={"provider_payment_method_id": method.provider_payment_method_id},
    )

    return CommercialPaymentMethodOut(**asdict(method))


@router.post("/subscription/{subscription_id}/convert-trial", response_model=CommercialSubscriptionOut)
async def convert_trial_route(
    subscription_id: str,
    payload: CommercialTrialConversionRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    subscription = await get_subscription_by_tenant(db, tenant_id=str(principal["tenant_id"]))
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    try:
        updated = await convert_trial_to_paid(
            db,
            tenant_id=str(principal["tenant_id"]),
            payment_method_id=payload.payment_method_id,
            plan_code=payload.plan_code,
        )
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc

    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.convert_trial",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=updated.id,
        status_code=status.HTTP_200_OK,
        message="Trial converted to paid subscription",
        meta={"state": updated.commercial_state},
    )

    return _to_subscription_out(updated)


@router.post("/subscription/change-plan", response_model=CommercialSubscriptionOut)
async def change_plan_route(
    payload: CommercialSubscriptionChangePlanRequest,
    request: Request,
    principal: dict = Depends(get_commercial_principal),
    db: AsyncSession = Depends(get_commercial_db),
) -> CommercialSubscriptionOut:
    try:
        updated = await change_subscription_plan(
            db,
            tenant_id=str(principal["tenant_id"]),
            new_plan_code=payload.new_plan_code,
            prorate=payload.prorate,
        )
    except ValueError as exc:
        raise _raise_for_commercial_error(exc) from exc

    await AuditService.log(
        db=db,
        tenant_id=str(principal["tenant_id"]),
        action="commercial.subscription.change_plan",
        actor_user_id=str(principal.get("sub")),
        request_id=getattr(request.state, "request_id", None),
        resource="subscription",
        resource_id=updated.id,
        status_code=status.HTTP_200_OK,
        message="Subscription plan changed",
        meta={"new_plan_code": payload.new_plan_code, "prorate": payload.prorate},
    )

    return _to_subscription_out(updated)

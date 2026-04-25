from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.payments.schemas import (
    InvoicePaymentCreateRequest,
    InvoicePaymentListResponse,
    InvoicePaymentOut,
    InvoicePaymentSummaryOut,
    PaymentGatewayProviderUpdateRequest,
    PaymentGatewaySettingsSnapshotOut,
    PaymentProviderFoundationSnapshotOut,
)
from app.payments.service import (
    create_invoice_payment,
    get_invoice_payment_summary,
    list_invoice_payments,
)
from app.payments.settings_service import (
    get_payment_gateway_settings,
    get_payment_provider_foundation,
    update_payment_gateway_provider,
)
from app.rbac.permissions import PERMISSION_BILLING_ACCESS

router = APIRouter(prefix="/payments", tags=["payments"])


def _raise_for_payment_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Invoice does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _raise_for_payment_settings_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Tenant not found"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get(
    "",
    response_model=InvoicePaymentListResponse,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def list_payments_route(
    invoice_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    method: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoicePaymentListResponse:
    try:
        result = await list_invoice_payments(
            db,
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            status=status_filter,
            method=method,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _raise_for_payment_service_error(exc) from exc

    return InvoicePaymentListResponse(
        items=[InvoicePaymentOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.post(
    "",
    response_model=InvoicePaymentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def create_payment_route(
    payload: InvoicePaymentCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoicePaymentOut:
    try:
        payment = await create_invoice_payment(
            db,
            tenant_id=tenant_id,
            invoice_id=payload.invoice_id,
            amount=payload.amount,
            currency=payload.currency,
            method=payload.method,
            status=payload.status,
            payment_date=payload.payment_date,
            external_reference=payload.external_reference,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_payment_service_error(exc) from exc

    return InvoicePaymentOut(**asdict(payment))


@router.get(
    "/invoices/{invoice_id}/summary",
    response_model=InvoicePaymentSummaryOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def get_invoice_payment_summary_route(
    invoice_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoicePaymentSummaryOut:
    try:
        summary = await get_invoice_payment_summary(
            db,
            tenant_id=tenant_id,
            invoice_id=invoice_id,
        )
    except ValueError as exc:
        raise _raise_for_payment_service_error(exc) from exc

    return InvoicePaymentSummaryOut(**asdict(summary))


@router.get(
    "/gateway-settings",
    response_model=PaymentGatewaySettingsSnapshotOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def get_payment_gateway_settings_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> PaymentGatewaySettingsSnapshotOut:
    try:
        snapshot = await get_payment_gateway_settings(
            db,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise _raise_for_payment_settings_error(exc) from exc

    return PaymentGatewaySettingsSnapshotOut(**asdict(snapshot))


@router.put(
    "/gateway-settings/{provider}",
    response_model=PaymentGatewaySettingsSnapshotOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def update_payment_gateway_provider_route(
    provider: str,
    payload: PaymentGatewayProviderUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> PaymentGatewaySettingsSnapshotOut:
    try:
        snapshot = await update_payment_gateway_provider(
            db,
            tenant_id=tenant_id,
            provider=provider,
            is_enabled=payload.is_enabled,
            is_default=payload.is_default,
            mode=payload.mode,
            account_id=payload.account_id,
            merchant_id=payload.merchant_id,
            publishable_key=payload.publishable_key,
            client_id=payload.client_id,
            secret_key=payload.secret_key,
            api_key=payload.api_key,
            client_secret=payload.client_secret,
            webhook_secret=payload.webhook_secret,
        )
    except ValueError as exc:
        raise _raise_for_payment_settings_error(exc) from exc

    return PaymentGatewaySettingsSnapshotOut(**asdict(snapshot))


@router.get(
    "/provider-foundation",
    response_model=PaymentProviderFoundationSnapshotOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def get_payment_provider_foundation_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> PaymentProviderFoundationSnapshotOut:
    try:
        snapshot = await get_payment_provider_foundation(
            db,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise _raise_for_payment_settings_error(exc) from exc

    return PaymentProviderFoundationSnapshotOut(**asdict(snapshot))

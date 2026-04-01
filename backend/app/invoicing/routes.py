from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.invoicing.schemas import (
    InvoiceCreateRequest,
    InvoiceListResponse,
    InvoiceOut,
    InvoiceStatusUpdateRequest,
    InvoiceUpdateRequest,
)
from app.invoicing.service import (
    create_invoice,
    delete_invoice,
    get_invoice_by_id,
    list_invoices,
    update_invoice,
    update_invoice_status,
)
from app.rbac.permissions import PERMISSION_BILLING_ACCESS
from app.sales.schemas import DeleteResponse

router = APIRouter(prefix="/invoices", tags=["invoicing"])


def _raise_for_invoice_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Invoice does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if detail.startswith("Company does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Contact does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Product does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Invalid invoice status transition"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Invalid invoice status"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Currency must be"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Due date cannot be earlier than issue date"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail in {"Company ID is required", "Failed to create invoice"}:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.post(
    "",
    response_model=InvoiceOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def create_invoice_route(
    payload: InvoiceCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoiceOut:
    try:
        invoice = await create_invoice(
            db,
            tenant_id=tenant_id,
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            product_id=payload.product_id,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            currency=payload.currency,
            total_amount=payload.total_amount,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_invoice_service_error(exc) from exc

    return InvoiceOut(**asdict(invoice))


@router.get(
    "",
    response_model=InvoiceListResponse,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def list_invoices_route(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: str | None = Query(default=None),
    number: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoiceListResponse:
    try:
        result = await list_invoices(
            db,
            tenant_id=tenant_id,
            q=q,
            status=status_filter,
            company_id=company_id,
            number_query=number,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _raise_for_invoice_service_error(exc) from exc

    return InvoiceListResponse(
        items=[InvoiceOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def get_invoice_route(
    invoice_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoiceOut:
    invoice = await get_invoice_by_id(
        db,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
    )
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    return InvoiceOut(**asdict(invoice))


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def update_invoice_route(
    invoice_id: str,
    payload: InvoiceUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoiceOut:
    try:
        invoice = await update_invoice(
            db,
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            product_id=payload.product_id,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            currency=payload.currency,
            total_amount=payload.total_amount,
            status=payload.status,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_invoice_service_error(exc) from exc

    return InvoiceOut(**asdict(invoice))


@router.patch(
    "/{invoice_id}/status",
    response_model=InvoiceOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def update_invoice_status_route(
    invoice_id: str,
    payload: InvoiceStatusUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoiceOut:
    try:
        invoice = await update_invoice_status(
            db,
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            status=payload.status,
        )
    except ValueError as exc:
        raise _raise_for_invoice_service_error(exc) from exc

    return InvoiceOut(**asdict(invoice))


@router.delete(
    "/{invoice_id}",
    response_model=DeleteResponse,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def delete_invoice_route(
    invoice_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DeleteResponse:
    deleted = await delete_invoice(
        db,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    return DeleteResponse(
        success=True,
        message="Invoice deleted successfully",
    )

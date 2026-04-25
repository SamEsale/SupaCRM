from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.invoicing.schemas import InvoiceOut
from app.quotes.schemas import (
    QuoteCreateRequest,
    QuoteListResponse,
    QuoteOut,
    QuoteStatusUpdateRequest,
    QuoteUpdateRequest,
)
from app.quotes.service import (
    create_quote,
    convert_deal_to_quote,
    convert_quote_to_invoice,
    delete_quote,
    get_quote_by_id,
    list_quotes,
    update_quote,
    update_quote_status,
)
from app.rbac.permissions import PERMISSION_BILLING_ACCESS
from app.sales.schemas import DeleteResponse

router = APIRouter(prefix="/quotes", tags=["quotes"])


def _raise_for_quote_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Quote does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if detail.startswith("Company does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Contact does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Contact does not belong to company"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Deal does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Deal does not belong to company"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Product does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Invalid quote status"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Invalid quote status transition"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Currency must be"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Only accepted quotes can be converted"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Expiry date cannot be earlier than issue date"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail in {"Company ID is required", "Failed to create quote"}:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.post(
    "",
    response_model=QuoteOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def create_quote_route(
    payload: QuoteCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> QuoteOut:
    try:
        quote = await create_quote(
            db,
            tenant_id=tenant_id,
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            deal_id=payload.deal_id,
            source_deal_id=payload.source_deal_id,
            product_id=payload.product_id,
            issue_date=payload.issue_date,
            expiry_date=payload.expiry_date,
            currency=payload.currency,
            total_amount=payload.total_amount,
            status=payload.status,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_quote_service_error(exc) from exc

    return QuoteOut(**asdict(quote))


@router.patch(
    "/{quote_id}",
    response_model=QuoteOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def update_quote_route(
    quote_id: str,
    payload: QuoteUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> QuoteOut:
    try:
        quote = await update_quote(
            db,
            tenant_id=tenant_id,
            quote_id=quote_id,
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            deal_id=payload.deal_id,
            product_id=payload.product_id,
            issue_date=payload.issue_date,
            expiry_date=payload.expiry_date,
            currency=payload.currency,
            total_amount=payload.total_amount,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_quote_service_error(exc) from exc

    return QuoteOut(**asdict(quote))


@router.get(
    "",
    response_model=QuoteListResponse,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def list_quotes_route(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: str | None = Query(default=None),
    number: str | None = Query(default=None),
    source_deal_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> QuoteListResponse:
    try:
        result = await list_quotes(
            db,
            tenant_id=tenant_id,
            q=q,
            status=status_filter,
            company_id=company_id,
            number_query=number,
            source_deal_id=source_deal_id,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _raise_for_quote_service_error(exc) from exc

    return QuoteListResponse(
        items=[QuoteOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.get(
    "/{quote_id}",
    response_model=QuoteOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def get_quote_route(
    quote_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> QuoteOut:
    quote = await get_quote_by_id(
        db,
        tenant_id=tenant_id,
        quote_id=quote_id,
    )
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    return QuoteOut(**asdict(quote))


@router.post(
    "/from-deal/{deal_id}",
    response_model=QuoteOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def convert_deal_to_quote_route(
    deal_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> QuoteOut:
    try:
        quote = await convert_deal_to_quote(
            db,
            tenant_id=tenant_id,
            deal_id=deal_id,
        )
    except ValueError as exc:
        raise _raise_for_quote_service_error(exc) from exc

    return QuoteOut(**asdict(quote))


@router.post(
    "/{quote_id}/convert-to-invoice",
    response_model=InvoiceOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def convert_quote_to_invoice_route(
    quote_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> InvoiceOut:
    try:
        invoice = await convert_quote_to_invoice(
            db,
            tenant_id=tenant_id,
            quote_id=quote_id,
        )
    except ValueError as exc:
        raise _raise_for_quote_service_error(exc) from exc

    return InvoiceOut(**asdict(invoice))


@router.delete(
    "/{quote_id}",
    response_model=DeleteResponse,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def delete_quote_route(
    quote_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DeleteResponse:
    deleted = await delete_quote(
        db,
        tenant_id=tenant_id,
        quote_id=quote_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    return DeleteResponse(
        success=True,
        message="Quote deleted successfully",
    )


@router.patch(
    "/{quote_id}/status",
    response_model=QuoteOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def update_quote_status_route(
    quote_id: str,
    payload: QuoteStatusUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> QuoteOut:
    try:
        quote = await update_quote_status(
            db,
            tenant_id=tenant_id,
            quote_id=quote_id,
            status=payload.status,
        )
    except ValueError as exc:
        raise _raise_for_quote_service_error(exc) from exc

    return QuoteOut(**asdict(quote))

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.rbac.permissions import PERMISSION_SALES_READ, PERMISSION_SALES_WRITE
from app.sales.schemas import (
    DealCreateRequest,
    DealListResponse,
    DealOut,
    DealUpdateRequest,
    DeleteResponse,
    PipelineReportResponse,
    PipelineStageCountOut,
)
from app.sales.service import (
    create_deal,
    delete_deal,
    get_deal_by_id,
    get_pipeline_report,
    list_deals,
    update_deal,
)

router = APIRouter(prefix="/sales", tags=["sales"])


def _raise_for_deal_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Deal does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if detail.startswith("Company does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Contact does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Product does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Invalid deal stage transition"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Invalid deal stage"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Invalid deal status"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Currency must be"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail in {"Deal name is required", "Company ID is required", "Failed to create deal"}:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get(
    "/probe",
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def sales_probe() -> dict:
    return {
        "module": "sales",
        "permission_required": PERMISSION_SALES_READ,
        "status": "ok",
    }


@router.get(
    "/pipeline-report",
    response_model=PipelineReportResponse,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def pipeline_report_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> PipelineReportResponse:
    result = await get_pipeline_report(
        db,
        tenant_id=tenant_id,
    )
    return PipelineReportResponse(
        items=[PipelineStageCountOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.post(
    "/deals",
    response_model=DealOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def create_deal_route(
    payload: DealCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DealOut:
    try:
        deal = await create_deal(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            product_id=payload.product_id,
            amount=payload.amount,
            currency=payload.currency,
            stage=payload.stage,
            status=payload.status,
            expected_close_date=payload.expected_close_date,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_deal_service_error(exc) from exc

    return DealOut(**asdict(deal))


@router.get(
    "/deals",
    response_model=DealListResponse,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def list_deals_route(
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DealListResponse:
    result = await list_deals(
        db,
        tenant_id=tenant_id,
        q=q,
        limit=limit,
        offset=offset,
    )
    return DealListResponse(
        items=[DealOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.get(
    "/deals/{deal_id}",
    response_model=DealOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def get_deal_route(
    deal_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DealOut:
    deal = await get_deal_by_id(
        db,
        tenant_id=tenant_id,
        deal_id=deal_id,
    )
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    return DealOut(**asdict(deal))


@router.patch(
    "/deals/{deal_id}",
    response_model=DealOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def update_deal_route(
    deal_id: str,
    payload: DealUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DealOut:
    try:
        deal = await update_deal(
            db,
            tenant_id=tenant_id,
            deal_id=deal_id,
            name=payload.name,
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            product_id=payload.product_id,
            amount=payload.amount,
            currency=payload.currency,
            stage=payload.stage,
            status=payload.status,
            expected_close_date=payload.expected_close_date,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_deal_service_error(exc) from exc

    return DealOut(**asdict(deal))


@router.delete(
    "/deals/{deal_id}",
    response_model=DeleteResponse,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def delete_deal_route(
    deal_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DeleteResponse:
    deleted = await delete_deal(
        db,
        tenant_id=tenant_id,
        deal_id=deal_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    return DeleteResponse(
        success=True,
        message="Deal deleted successfully",
    )
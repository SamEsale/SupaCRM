from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.rbac.permissions import PERMISSION_SALES_READ, PERMISSION_SALES_WRITE
from app.sales.schemas import (
    DealCreateRequest,
    DealFollowUpUpdateRequest,
    LeadImportRequest,
    LeadImportResultOut,
    LeadImportRowOut,
    DealListResponse,
    DealListView,
    DealOut,
    DealUpdateRequest,
    DeleteResponse,
    LeadCreateRequest,
    PipelineReportResponse,
    PipelineStageCountOut,
    SalesForecastReportResponse,
    SalesForecastSummaryOut,
    SalesStageSummaryOut,
)
from app.sales.service import (
    create_deal,
    create_lead_from_intake,
    delete_deal,
    export_leads_csv,
    get_deal_by_id,
    get_pipeline_report,
    get_sales_forecast_report,
    import_leads_from_csv,
    list_deals,
    update_deal_follow_up,
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

    if detail.startswith("Contact does not belong to the selected company"):
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


def _raise_for_deal_integrity_error(exc: IntegrityError) -> HTTPException:
    detail = str(getattr(exc, "orig", exc))

    if "ck_deals_stage_valid" in detail:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deal stage. The current deal stage contract is out of sync with persistence constraints.",
        )

    if "ck_deals_status_valid" in detail:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deal status. The current deal status contract is out of sync with persistence constraints.",
        )

    raise exc


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


@router.get(
    "/forecast-report",
    response_model=SalesForecastReportResponse,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def forecast_report_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SalesForecastReportResponse:
    result = await get_sales_forecast_report(
        db,
        tenant_id=tenant_id,
    )
    return SalesForecastReportResponse(
        summary=SalesForecastSummaryOut(**asdict(result.summary)),
        stage_breakdown=[SalesStageSummaryOut(**asdict(item)) for item in result.stage_breakdown],
        opportunity_stage_breakdown=[
            SalesStageSummaryOut(**asdict(item)) for item in result.opportunity_stage_breakdown
        ],
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
    except IntegrityError as exc:
        raise _raise_for_deal_integrity_error(exc) from exc

    return DealOut(**asdict(deal))


@router.post(
    "/leads",
    response_model=DealOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def create_lead_route(
    payload: LeadCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DealOut:
    try:
        deal = await create_lead_from_intake(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            email=str(payload.email) if payload.email else None,
            phone=payload.phone,
            amount=payload.amount,
            currency=payload.currency,
            source=payload.source,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_deal_service_error(exc) from exc
    except IntegrityError as exc:
        raise _raise_for_deal_integrity_error(exc) from exc

    return DealOut(**asdict(deal))


@router.post(
    "/leads/import",
    response_model=LeadImportResultOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def import_leads_route(
    payload: LeadImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> LeadImportResultOut:
    try:
        result = await import_leads_from_csv(
            db,
            tenant_id=tenant_id,
            csv_text=payload.csv_text,
            create_missing_companies=payload.create_missing_companies,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return LeadImportResultOut(
        total_rows=result.total_rows,
        imported_rows=result.imported_rows,
        error_rows=result.error_rows,
        rows=[LeadImportRowOut(**asdict(item)) for item in result.rows],
    )


@router.get(
    "/leads/export",
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def export_leads_route(
    q: str | None = Query(default=None),
    company_id: str | None = Query(default=None),
    contact_id: str | None = Query(default=None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> Response:
    csv_text, row_count = await export_leads_csv(
        db,
        tenant_id=tenant_id,
        q=q,
        company_id=company_id,
        contact_id=contact_id,
    )
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="leads-export.csv"',
            "X-SupaCRM-Row-Count": str(row_count),
        },
    )


@router.get(
    "/deals",
    response_model=DealListResponse,
    dependencies=[Depends(require_permission(PERMISSION_SALES_READ))],
)
async def list_deals_route(
    view: DealListView = Query(default="all"),
    q: str | None = Query(default=None),
    company_id: str | None = Query(default=None),
    contact_id: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DealListResponse:
    result = await list_deals(
        db,
        tenant_id=tenant_id,
        view=view,
        q=q,
        company_id=company_id,
        contact_id=contact_id,
        product_id=product_id,
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
    except IntegrityError as exc:
        raise _raise_for_deal_integrity_error(exc) from exc

    return DealOut(**asdict(deal))


@router.patch(
    "/deals/{deal_id}/follow-up",
    response_model=DealOut,
    dependencies=[Depends(require_permission(PERMISSION_SALES_WRITE))],
)
async def update_deal_follow_up_route(
    deal_id: str,
    payload: DealFollowUpUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DealOut:
    try:
        deal = await update_deal_follow_up(
            db,
            tenant_id=tenant_id,
            deal_id=deal_id,
            next_follow_up_at=payload.next_follow_up_at,
            follow_up_note=payload.follow_up_note,
        )
    except ValueError as exc:
        raise _raise_for_deal_service_error(exc) from exc
    except IntegrityError as exc:
        raise _raise_for_deal_integrity_error(exc) from exc

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

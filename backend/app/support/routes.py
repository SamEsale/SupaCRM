from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.rbac.permissions import PERMISSION_SUPPORT_READ, PERMISSION_SUPPORT_WRITE
from app.support.schemas import (
    SupportSummaryOut,
    SupportTicketCreateRequest,
    SupportTicketListResponse,
    SupportTicketOut,
    SupportTicketUpdateRequest,
)
from app.support.service import (
    create_ticket,
    get_support_summary,
    get_ticket_by_id,
    list_tickets,
    update_ticket,
)

router = APIRouter(prefix="/support", tags=["support"])


def _raise_for_support_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Ticket does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get(
    "/probe",
    dependencies=[Depends(require_permission(PERMISSION_SUPPORT_READ))],
)
async def support_probe() -> dict:
    return {
        "module": "support",
        "permission_required": PERMISSION_SUPPORT_READ,
        "status": "ok",
    }


@router.get(
    "/summary",
    response_model=SupportSummaryOut,
    dependencies=[Depends(require_permission(PERMISSION_SUPPORT_READ))],
)
async def support_summary_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SupportSummaryOut:
    summary = await get_support_summary(db, tenant_id=tenant_id)
    return SupportSummaryOut(**asdict(summary))


@router.get(
    "/tickets",
    response_model=SupportTicketListResponse,
    dependencies=[Depends(require_permission(PERMISSION_SUPPORT_READ))],
)
async def list_tickets_route(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SupportTicketListResponse:
    try:
        result = await list_tickets(
            db,
            tenant_id=tenant_id,
            q=q,
            status=status_filter,
            priority=priority,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _raise_for_support_service_error(exc) from exc
    return SupportTicketListResponse(
        items=[SupportTicketOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.post(
    "/tickets",
    response_model=SupportTicketOut,
    dependencies=[Depends(require_permission(PERMISSION_SUPPORT_WRITE))],
)
async def create_ticket_route(
    payload: SupportTicketCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SupportTicketOut:
    try:
        ticket = await create_ticket(
            db,
            tenant_id=tenant_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            source=payload.source,
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            assigned_to_user_id=payload.assigned_to_user_id,
            related_deal_id=payload.related_deal_id,
            related_invoice_id=payload.related_invoice_id,
        )
    except ValueError as exc:
        raise _raise_for_support_service_error(exc) from exc
    return SupportTicketOut(**asdict(ticket))


@router.get(
    "/tickets/{ticket_id}",
    response_model=SupportTicketOut,
    dependencies=[Depends(require_permission(PERMISSION_SUPPORT_READ))],
)
async def get_ticket_route(
    ticket_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SupportTicketOut:
    ticket = await get_ticket_by_id(db, tenant_id=tenant_id, ticket_id=ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return SupportTicketOut(**asdict(ticket))


@router.patch(
    "/tickets/{ticket_id}",
    response_model=SupportTicketOut,
    dependencies=[Depends(require_permission(PERMISSION_SUPPORT_WRITE))],
)
async def update_ticket_route(
    ticket_id: str,
    payload: SupportTicketUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SupportTicketOut:
    try:
        updates = payload.model_dump(exclude_unset=True)
        ticket = await update_ticket(
            db,
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            **updates,
        )
    except ValueError as exc:
        raise _raise_for_support_service_error(exc) from exc
    return SupportTicketOut(**asdict(ticket))

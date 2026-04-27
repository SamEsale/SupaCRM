from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.expenses.schemas import (
    ExpenseCreateRequest,
    ExpenseListResponse,
    ExpenseOut,
    ExpenseUpdateRequest,
)
from app.expenses.service import create_expense, get_expense, list_expenses, update_expense
from app.rbac.permissions import PERMISSION_BILLING_ACCESS

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _raise_for_expense_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Expense does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if detail.startswith("Paid expenses are locked"):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.post(
    "",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def create_expense_route(
    payload: ExpenseCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ExpenseOut:
    try:
        expense = await create_expense(
            db,
            tenant_id=tenant_id,
            title=payload.title,
            description=payload.description,
            amount=payload.amount,
            currency=payload.currency,
            expense_date=payload.expense_date,
            category=payload.category,
            status=payload.status,
            vendor_name=payload.vendor_name,
        )
    except ValueError as exc:
        raise _raise_for_expense_service_error(exc) from exc

    return ExpenseOut(**asdict(expense))


@router.get(
    "",
    response_model=ExpenseListResponse,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def list_expenses_route(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ExpenseListResponse:
    try:
        result = await list_expenses(
            db,
            tenant_id=tenant_id,
            status=status_filter,
            category=category,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _raise_for_expense_service_error(exc) from exc

    return ExpenseListResponse(
        items=[ExpenseOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.get(
    "/{expense_id}",
    response_model=ExpenseOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def get_expense_route(
    expense_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ExpenseOut:
    try:
        expense = await get_expense(db, tenant_id=tenant_id, expense_id=expense_id)
    except ValueError as exc:
        raise _raise_for_expense_service_error(exc) from exc

    return ExpenseOut(**asdict(expense))


@router.patch(
    "/{expense_id}",
    response_model=ExpenseOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def update_expense_route(
    expense_id: str,
    payload: ExpenseUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ExpenseOut:
    try:
        expense = await update_expense(
            db,
            tenant_id=tenant_id,
            expense_id=expense_id,
            title=payload.title,
            description=payload.description,
            amount=payload.amount,
            currency=payload.currency,
            expense_date=payload.expense_date,
            category=payload.category,
            status=payload.status,
            vendor_name=payload.vendor_name,
        )
    except ValueError as exc:
        raise _raise_for_expense_service_error(exc) from exc

    return ExpenseOut(**asdict(expense))

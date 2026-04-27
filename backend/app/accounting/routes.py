from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import (
    AccountingAccountCreateRequest,
    AccountingAccountListResponse,
    AccountingAccountOut,
    JournalEntryListResponse,
    JournalEntryOut,
)
from app.accounting.service import create_account, list_accounts, list_journal_entries
from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.rbac.permissions import PERMISSION_BILLING_ACCESS

router = APIRouter(prefix="/accounting", tags=["accounting"])


def _raise_for_accounting_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Invalid account type"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Account code already exists"):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    if detail.startswith("Account code is required") or detail.startswith("Account name is required"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if detail.startswith("Journal entry does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get(
    "/accounts",
    response_model=AccountingAccountListResponse,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def list_accounts_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> AccountingAccountListResponse:
    result = await list_accounts(db, tenant_id=tenant_id)
    return AccountingAccountListResponse(
        items=[AccountingAccountOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.post(
    "/accounts",
    response_model=AccountingAccountOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def create_account_route(
    payload: AccountingAccountCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> AccountingAccountOut:
    try:
        account = await create_account(
            db,
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            account_type=payload.account_type,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise _raise_for_accounting_service_error(exc) from exc

    return AccountingAccountOut(**asdict(account))


@router.get(
    "/journal-entries",
    response_model=JournalEntryListResponse,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def list_journal_entries_route(
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    source_event: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> JournalEntryListResponse:
    try:
        result = await list_journal_entries(
            db,
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id,
            source_event=source_event,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _raise_for_accounting_service_error(exc) from exc

    return JournalEntryListResponse(
        items=[JournalEntryOut(**asdict(item)) for item in result.items],
        total=result.total,
    )

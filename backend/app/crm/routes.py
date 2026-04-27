from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.crm.schemas import (
    CompanyCreateRequest,
    ContactImportRequest,
    ContactImportResultOut,
    ContactImportRowOut,
    CompanyListResponse,
    CompanyOut,
    CompanyUpdateRequest,
    ContactCreateRequest,
    ContactListResponse,
    ContactOut,
    ContactUpdateRequest,
    DeleteResponse,
)
from app.crm.service import (
    create_company,
    create_contact,
    delete_company,
    delete_contact,
    export_contacts_csv,
    get_company_by_id,
    get_contact_by_id,
    import_contacts_from_csv,
    list_companies,
    list_contacts,
    update_company,
    update_contact,
)
from app.db_deps import get_auth_db
from app.rbac.permissions import PERMISSION_CRM_READ, PERMISSION_CRM_WRITE

router = APIRouter(prefix="/crm", tags=["crm"])


def _raise_for_contact_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Contact does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if detail.startswith("Company does not exist"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if "already exists for this tenant" in detail:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _raise_for_company_service_error(exc: ValueError) -> HTTPException:
    detail = str(exc)

    if detail.startswith("Company does not exist"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if "already exists for this tenant" in detail:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.post(
    "/contacts",
    response_model=ContactOut,
    dependencies=[Depends(require_permission(PERMISSION_CRM_WRITE))],
)
async def create_contact_route(
    payload: ContactCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ContactOut:
    try:
        contact = await create_contact(
            db,
            tenant_id=tenant_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=str(payload.email) if payload.email is not None else None,
            phone=payload.phone,
            company_id=payload.company_id,
            company=payload.company,
            job_title=payload.job_title,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_contact_service_error(exc) from exc

    return ContactOut(**asdict(contact))


@router.get(
    "/contacts",
    response_model=ContactListResponse,
    dependencies=[Depends(require_permission(PERMISSION_CRM_READ))],
)
async def list_contacts_route(
    q: str | None = Query(default=None),
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ContactListResponse:
    result = await list_contacts(
        db,
        tenant_id=tenant_id,
        q=q,
        company_id=company_id,
        limit=limit,
        offset=offset,
    )
    return ContactListResponse(
        items=[ContactOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.post(
    "/contacts/import",
    response_model=ContactImportResultOut,
    dependencies=[Depends(require_permission(PERMISSION_CRM_WRITE))],
)
async def import_contacts_route(
    payload: ContactImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ContactImportResultOut:
    try:
        result = await import_contacts_from_csv(
            db,
            tenant_id=tenant_id,
            csv_text=payload.csv_text,
            create_missing_companies=payload.create_missing_companies,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ContactImportResultOut(
        total_rows=result.total_rows,
        imported_rows=result.imported_rows,
        error_rows=result.error_rows,
        rows=[ContactImportRowOut(**asdict(item)) for item in result.rows],
    )


@router.get(
    "/contacts/export",
    dependencies=[Depends(require_permission(PERMISSION_CRM_READ))],
)
async def export_contacts_route(
    q: str | None = Query(default=None),
    company_id: str | None = Query(default=None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> Response:
    csv_text, row_count = await export_contacts_csv(
        db,
        tenant_id=tenant_id,
        q=q,
        company_id=company_id,
    )
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="contacts-export.csv"',
            "X-SupaCRM-Row-Count": str(row_count),
        },
    )


@router.get(
    "/contacts/{contact_id}",
    response_model=ContactOut,
    dependencies=[Depends(require_permission(PERMISSION_CRM_READ))],
)
async def get_contact_route(
    contact_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ContactOut:
    contact = await get_contact_by_id(
        db,
        tenant_id=tenant_id,
        contact_id=contact_id,
    )
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    return ContactOut(**asdict(contact))


@router.patch(
    "/contacts/{contact_id}",
    response_model=ContactOut,
    dependencies=[Depends(require_permission(PERMISSION_CRM_WRITE))],
)
async def update_contact_route(
    contact_id: str,
    payload: ContactUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ContactOut:
    try:
        contact = await update_contact(
            db,
            tenant_id=tenant_id,
            contact_id=contact_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=str(payload.email) if payload.email is not None else None,
            phone=payload.phone,
            company_id=payload.company_id,
            company=payload.company,
            job_title=payload.job_title,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_contact_service_error(exc) from exc

    return ContactOut(**asdict(contact))


@router.delete(
    "/contacts/{contact_id}",
    response_model=DeleteResponse,
    dependencies=[Depends(require_permission(PERMISSION_CRM_WRITE))],
)
async def delete_contact_route(
    contact_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DeleteResponse:
    try:
        deleted = await delete_contact(
            db,
            tenant_id=tenant_id,
            contact_id=contact_id,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete contact because it is referenced by one or more records.",
        ) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    return DeleteResponse(
        success=True,
        message="Contact deleted successfully",
    )


@router.post(
    "/companies",
    response_model=CompanyOut,
    dependencies=[Depends(require_permission(PERMISSION_CRM_WRITE))],
)
async def create_company_route(
    payload: CompanyCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> CompanyOut:
    try:
        company = await create_company(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            website=payload.website,
            email=str(payload.email) if payload.email is not None else None,
            phone=payload.phone,
            industry=payload.industry,
            address=payload.address,
            vat_number=payload.vat_number,
            registration_number=payload.registration_number,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_company_service_error(exc) from exc

    return CompanyOut(**asdict(company))


@router.get(
    "/companies",
    response_model=CompanyListResponse,
    dependencies=[Depends(require_permission(PERMISSION_CRM_READ))],
)
async def list_companies_route(
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> CompanyListResponse:
    result = await list_companies(
        db,
        tenant_id=tenant_id,
        q=q,
        limit=limit,
        offset=offset,
    )
    return CompanyListResponse(
        items=[CompanyOut(**asdict(item)) for item in result.items],
        total=result.total,
    )


@router.get(
    "/companies/{company_id}",
    response_model=CompanyOut,
    dependencies=[Depends(require_permission(PERMISSION_CRM_READ))],
)
async def get_company_route(
    company_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> CompanyOut:
    company = await get_company_by_id(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
    )
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    return CompanyOut(**asdict(company))


@router.patch(
    "/companies/{company_id}",
    response_model=CompanyOut,
    dependencies=[Depends(require_permission(PERMISSION_CRM_WRITE))],
)
async def update_company_route(
    company_id: str,
    payload: CompanyUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> CompanyOut:
    try:
        company = await update_company(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            name=payload.name,
            website=payload.website,
            email=str(payload.email) if payload.email is not None else None,
            phone=payload.phone,
            industry=payload.industry,
            address=payload.address,
            vat_number=payload.vat_number,
            registration_number=payload.registration_number,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise _raise_for_company_service_error(exc) from exc

    return CompanyOut(**asdict(company))


@router.delete(
    "/companies/{company_id}",
    response_model=DeleteResponse,
    dependencies=[Depends(require_permission(PERMISSION_CRM_WRITE))],
)
async def delete_company_route(
    company_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> DeleteResponse:
    try:
        deleted = await delete_company(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete company because it is referenced by one or more records.",
        ) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    return DeleteResponse(
        success=True,
        message="Company deleted successfully",
    )

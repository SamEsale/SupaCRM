from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.schemas import (
    ProductCreateRequest,
    ProductDeleteResponse,
    ProductListResponse,
    ProductOut,
    ProductUpdateRequest,
)
from app.catalog.service import (
    create_product,
    delete_product,
    get_product,
    list_products,
    update_product,
)
from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.rbac.permissions import PERMISSION_TENANT_ADMIN

router = APIRouter(prefix="/products", tags=["catalog"])


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def create_catalog_product(
    payload: ProductCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ProductOut:
    try:
        product = await create_product(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            sku=payload.sku,
            description=payload.description,
            unit_price=payload.unit_price,
            currency=payload.currency,
            is_active=payload.is_active,
            images=[image.model_dump() for image in payload.images],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ProductOut(**asdict(product))


@router.get(
    "",
    response_model=ProductListResponse,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def list_catalog_products(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ProductListResponse:
    products = await list_products(db, tenant_id=tenant_id)
    items = [ProductOut(**asdict(product)) for product in products]
    return ProductListResponse(items=items, total=len(items))


@router.get(
    "/{product_id}",
    response_model=ProductOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def get_catalog_product(
    product_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ProductOut:
    product = await get_product(db, tenant_id=tenant_id, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductOut(**asdict(product))


@router.put(
    "/{product_id}",
    response_model=ProductOut,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def update_catalog_product(
    product_id: str,
    payload: ProductUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ProductOut:
    try:
        product = await update_product(
            db,
            tenant_id=tenant_id,
            product_id=product_id,
            name=payload.name,
            sku=payload.sku,
            description=payload.description,
            unit_price=payload.unit_price,
            currency=payload.currency,
            is_active=payload.is_active,
            images=None if payload.images is None else [image.model_dump() for image in payload.images],
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "Product not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

    return ProductOut(**asdict(product))


@router.delete(
    "/{product_id}",
    response_model=ProductDeleteResponse,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def delete_catalog_product(
    product_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ProductDeleteResponse:
    try:
        deleted = await delete_product(db, tenant_id=tenant_id, product_id=product_id)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete product because it is referenced by one or more deals.",
        ) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return ProductDeleteResponse(
        success=True,
        message="Product deleted successfully",
    )

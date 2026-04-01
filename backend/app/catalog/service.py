from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import ProductImageRecord, ProductRecord


def _normalize_images(images: list[dict]) -> list[dict]:
    if len(images) > 15:
        raise ValueError("Maximum 15 product images are allowed")

    positions = [int(image["position"]) for image in images]

    if any(position < 1 or position > 15 for position in positions):
        raise ValueError("Product image positions must be between 1 and 15")

    if len(positions) != len(set(positions)):
        raise ValueError("Product image positions must be unique")

    normalized: list[dict] = []
    for image in images:
        file_key = str(image["file_key"]).strip()
        if not file_key:
            raise ValueError("Product image file_key is required")

        normalized.append(
            {
                "position": int(image["position"]),
                "file_key": file_key,
            }
        )

    return normalized


def _build_product_record(product_row: dict, image_rows: list[dict]) -> ProductRecord:
    images = [
        ProductImageRecord(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            product_id=str(row["product_id"]),
            position=int(row["position"]),
            file_key=str(row["file_key"]),
            created_at=row["created_at"],
        )
        for row in sorted(image_rows, key=lambda item: int(item["position"]))
    ]

    return ProductRecord(
        id=str(product_row["id"]),
        tenant_id=str(product_row["tenant_id"]),
        name=str(product_row["name"]),
        sku=str(product_row["sku"]),
        description=product_row["description"],
        unit_price=Decimal(product_row["unit_price"]),
        currency=str(product_row["currency"]),
        is_active=bool(product_row["is_active"]),
        created_at=product_row["created_at"],
        updated_at=product_row["updated_at"],
        images=images,
    )


async def _get_product_row(
    db: AsyncSession,
    *,
    tenant_id: str,
    product_id: str,
) -> dict | None:
    result = await db.execute(
        text(
            """
            select
                p.id,
                p.tenant_id,
                p.name,
                p.sku,
                p.description,
                p.unit_price,
                p.currency,
                p.is_active,
                p.created_at,
                p.updated_at
            from public.products p
            where p.tenant_id = cast(:tenant_id as varchar)
              and p.id = cast(:product_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "product_id": product_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _get_product_images(
    db: AsyncSession,
    *,
    tenant_id: str,
    product_id: str,
) -> list[dict]:
    result = await db.execute(
        text(
            """
            select
                pi.id,
                pi.tenant_id,
                pi.product_id,
                pi.position,
                pi.file_key,
                pi.created_at
            from public.product_images pi
            where pi.tenant_id = cast(:tenant_id as varchar)
              and pi.product_id = cast(:product_id as varchar)
            order by pi.position
            """
        ),
        {"tenant_id": tenant_id, "product_id": product_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def _ensure_unique_sku(
    db: AsyncSession,
    *,
    tenant_id: str,
    sku: str,
    exclude_product_id: str | None = None,
) -> None:
    query = """
        select p.id
        from public.products p
        where p.tenant_id = cast(:tenant_id as varchar)
          and upper(p.sku) = :sku
    """
    params = {
        "tenant_id": tenant_id,
        "sku": sku.upper(),
    }

    if exclude_product_id:
        query += " and p.id <> cast(:exclude_product_id as varchar)"
        params["exclude_product_id"] = exclude_product_id

    result = await db.execute(text(query), params)
    existing_id = result.scalar_one_or_none()
    if existing_id is not None:
        raise ValueError("Product SKU already exists in this tenant")


async def create_product(
    db: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    sku: str,
    description: str | None,
    unit_price: Decimal,
    currency: str,
    is_active: bool,
    images: list[dict],
) -> ProductRecord:
    normalized_images = _normalize_images(images)
    normalized_name = name.strip()
    normalized_sku = sku.strip().upper()
    normalized_currency = currency.strip().upper()

    await _ensure_unique_sku(db, tenant_id=tenant_id, sku=normalized_sku)

    product_id = str(uuid.uuid4())

    try:
        await db.execute(
            text(
                """
                insert into public.products (
                    id,
                    tenant_id,
                    name,
                    sku,
                    description,
                    unit_price,
                    currency,
                    is_active
                )
                values (
                    cast(:id as varchar),
                    cast(:tenant_id as varchar),
                    cast(:name as varchar),
                    cast(:sku as varchar),
                    :description,
                    :unit_price,
                    cast(:currency as varchar),
                    :is_active
                )
                """
            ),
            {
                "id": product_id,
                "tenant_id": tenant_id,
                "name": normalized_name,
                "sku": normalized_sku,
                "description": description,
                "unit_price": unit_price,
                "currency": normalized_currency,
                "is_active": is_active,
            },
        )

        for image in normalized_images:
            await db.execute(
                text(
                    """
                    insert into public.product_images (
                        id,
                        tenant_id,
                        product_id,
                        position,
                        file_key
                    )
                    values (
                        cast(:id as varchar),
                        cast(:tenant_id as varchar),
                        cast(:product_id as varchar),
                        :position,
                        cast(:file_key as varchar)
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "product_id": product_id,
                    "position": image["position"],
                    "file_key": image["file_key"],
                },
            )

        product_row = await _get_product_row(db, tenant_id=tenant_id, product_id=product_id)
        if product_row is None:
            raise ValueError("Product was created but could not be retrieved")

        image_rows = await _get_product_images(db, tenant_id=tenant_id, product_id=product_id)
        product = _build_product_record(product_row, image_rows)

        await db.commit()
        return product
    except Exception:
        await db.rollback()
        raise


async def list_products(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> list[ProductRecord]:
    result = await db.execute(
        text(
            """
            select
                p.id,
                p.tenant_id,
                p.name,
                p.sku,
                p.description,
                p.unit_price,
                p.currency,
                p.is_active,
                p.created_at,
                p.updated_at
            from public.products p
            where p.tenant_id = cast(:tenant_id as varchar)
            order by p.created_at desc, p.name asc
            """
        ),
        {"tenant_id": tenant_id},
    )
    product_rows = [dict(row) for row in result.mappings().all()]

    products: list[ProductRecord] = []
    for product_row in product_rows:
        image_rows = await _get_product_images(
            db,
            tenant_id=tenant_id,
            product_id=str(product_row["id"]),
        )
        products.append(_build_product_record(product_row, image_rows))

    return products


async def get_product(
    db: AsyncSession,
    *,
    tenant_id: str,
    product_id: str,
) -> ProductRecord | None:
    product_row = await _get_product_row(db, tenant_id=tenant_id, product_id=product_id)
    if product_row is None:
        return None

    image_rows = await _get_product_images(db, tenant_id=tenant_id, product_id=product_id)
    return _build_product_record(product_row, image_rows)


async def update_product(
    db: AsyncSession,
    *,
    tenant_id: str,
    product_id: str,
    name: str | None = None,
    sku: str | None = None,
    description: str | None = None,
    unit_price: Decimal | None = None,
    currency: str | None = None,
    is_active: bool | None = None,
    images: list[dict] | None = None,
) -> ProductRecord:
    existing = await get_product(db, tenant_id=tenant_id, product_id=product_id)
    if existing is None:
        raise ValueError("Product not found")

    new_name = existing.name if name is None else name.strip()
    new_sku = existing.sku if sku is None else sku.strip().upper()
    new_description = existing.description if description is None else description
    new_unit_price = existing.unit_price if unit_price is None else unit_price
    new_currency = existing.currency if currency is None else currency.strip().upper()
    new_is_active = existing.is_active if is_active is None else is_active

    await _ensure_unique_sku(
        db,
        tenant_id=tenant_id,
        sku=new_sku,
        exclude_product_id=product_id,
    )

    try:
        await db.execute(
            text(
                """
                update public.products
                set name = cast(:name as varchar),
                    sku = cast(:sku as varchar),
                    description = :description,
                    unit_price = :unit_price,
                    currency = cast(:currency as varchar),
                    is_active = :is_active,
                    updated_at = now()
                where tenant_id = cast(:tenant_id as varchar)
                  and id = cast(:product_id as varchar)
                """
            ),
            {
                "tenant_id": tenant_id,
                "product_id": product_id,
                "name": new_name,
                "sku": new_sku,
                "description": new_description,
                "unit_price": new_unit_price,
                "currency": new_currency,
                "is_active": new_is_active,
            },
        )

        if images is not None:
            normalized_images = _normalize_images(images)

            await db.execute(
                text(
                    """
                    delete from public.product_images
                    where tenant_id = cast(:tenant_id as varchar)
                      and product_id = cast(:product_id as varchar)
                    """
                ),
                {"tenant_id": tenant_id, "product_id": product_id},
            )

            for image in normalized_images:
                await db.execute(
                    text(
                        """
                        insert into public.product_images (
                            id,
                            tenant_id,
                            product_id,
                            position,
                            file_key
                        )
                        values (
                            cast(:id as varchar),
                            cast(:tenant_id as varchar),
                            cast(:product_id as varchar),
                            :position,
                            cast(:file_key as varchar)
                        )
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": tenant_id,
                        "product_id": product_id,
                        "position": image["position"],
                        "file_key": image["file_key"],
                    },
                )

        product_row = await _get_product_row(db, tenant_id=tenant_id, product_id=product_id)
        if product_row is None:
            raise ValueError("Updated product could not be retrieved")

        image_rows = await _get_product_images(db, tenant_id=tenant_id, product_id=product_id)
        product = _build_product_record(product_row, image_rows)

        await db.commit()
        return product
    except Exception:
        await db.rollback()
        raise


async def delete_product(
    db: AsyncSession,
    *,
    tenant_id: str,
    product_id: str,
) -> bool:
    existing = await _get_product_row(db, tenant_id=tenant_id, product_id=product_id)
    if existing is None:
        return False

    try:
        await db.execute(
            text(
                """
                delete from public.product_images
                where tenant_id = cast(:tenant_id as varchar)
                  and product_id = cast(:product_id as varchar)
                """
            ),
            {"tenant_id": tenant_id, "product_id": product_id},
        )

        await db.execute(
            text(
                """
                delete from public.products
                where tenant_id = cast(:tenant_id as varchar)
                  and id = cast(:product_id as varchar)
                """
            ),
            {"tenant_id": tenant_id, "product_id": product_id},
        )

        await db.commit()
        return True
    except Exception:
        await db.rollback()
        raise
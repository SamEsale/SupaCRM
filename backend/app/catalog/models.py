from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class ProductImageRecord:
    id: str
    tenant_id: str
    product_id: str
    position: int
    file_key: str
    created_at: datetime


@dataclass(slots=True)
class ProductRecord:
    id: str
    tenant_id: str
    name: str
    sku: str
    description: str | None
    unit_price: Decimal
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageRecord] = field(default_factory=list)
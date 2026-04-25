from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.catalog.image_rules import validate_product_image_count


class ProductImageIn(BaseModel):
    position: int = Field(..., ge=1, le=15)
    file_key: str = Field(..., min_length=1, max_length=512)
    file_url: str | None = Field(default=None, max_length=2048)

    @field_validator("file_key")
    @classmethod
    def strip_file_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("file_key cannot be empty")
        return value


class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    unit_price: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    is_active: bool = True
    images: list[ProductImageIn]

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", "sku")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_images(self) -> "ProductCreateRequest":
        validate_product_image_count(len(self.images))

        positions = [image.position for image in self.images]

        if len(positions) != len(set(positions)):
            raise ValueError("Product image positions must be unique")

        return self


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
    images: list[ProductImageIn] | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("name", "sku")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_images_if_present(self) -> "ProductUpdateRequest":
        if self.images is None:
            return self

        validate_product_image_count(len(self.images))

        positions = [image.position for image in self.images]

        if len(positions) != len(set(positions)):
            raise ValueError("Product image positions must be unique")

        return self


class ProductImageOut(BaseModel):
    id: str
    tenant_id: str
    product_id: str
    position: int
    file_key: str
    created_at: datetime
    file_url: str | None = None


class ProductOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    sku: str
    description: str | None = None
    unit_price: Decimal
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageOut]


class ProductListResponse(BaseModel):
    items: list[ProductOut]
    total: int


class ProductDeleteResponse(BaseModel):
    success: bool
    message: str

from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# TALLA
# =========================================================

class VariantSizeResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# COLOR
# =========================================================

class VariantColorResponse(BaseModel):
    id: int
    name: str
    hex_code: str | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CREAR VARIANTE
# =========================================================

class ProductVariantCreate(BaseModel):
    size_id: int = Field(
        gt=0,
    )

    color_id: int = Field(
        gt=0,
    )

    sku: str = Field(
        min_length=1,
        max_length=80,
    )

    additional_price: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# ACTUALIZAR VARIANTE
# =========================================================

class ProductVariantUpdate(BaseModel):
    size_id: int | None = Field(
        default=None,
        gt=0,
    )

    color_id: int | None = Field(
        default=None,
        gt=0,
    )

    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
    )

    additional_price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# RESPUESTA
# =========================================================

class ProductVariantResponse(BaseModel):
    id: int

    product_id: int

    size_id: int

    color_id: int

    sku: str

    additional_price: Decimal

    image_url: str | None

    cloudinary_public_id: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    size: VariantSizeResponse

    color: VariantColorResponse

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LISTA
# =========================================================

class ProductVariantListResponse(BaseModel):
    items: list[ProductVariantResponse]

    total: int
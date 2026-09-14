from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# TIPOS
# =========================================================

AvailabilityStatus = Literal[
    "AVAILABLE",
    "LOW_STOCK",
    "OUT_OF_STOCK",
]


# =========================================================
# RESUMEN PROVEEDOR
# =========================================================

class AvailabilitySupplierSummary(BaseModel):
    id: int

    name: str

    nit: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN PRODUCTO
# =========================================================

class AvailabilityProductSummary(BaseModel):
    id: int

    code: str

    name: str

    brand: str | None = None

    cover_image_url: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN PRODUCTO DEL PROVEEDOR
# =========================================================

class AvailabilitySupplierProductSummary(BaseModel):
    id: int

    supplier_id: int

    product_id: int

    supplier_code: str | None = None

    purchase_price: Decimal

    is_active: bool

    supplier: AvailabilitySupplierSummary

    product: AvailabilityProductSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN TALLA
# =========================================================

class AvailabilitySizeSummary(BaseModel):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN COLOR
# =========================================================

class AvailabilityColorSummary(BaseModel):
    id: int

    name: str

    hex_code: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN VARIANTE
# =========================================================

class AvailabilityVariantSummary(BaseModel):
    id: int

    product_id: int

    size_id: int

    color_id: int

    sku: str

    additional_price: Decimal

    image_url: str | None = None

    is_active: bool

    size: AvailabilitySizeSummary

    color: AvailabilityColorSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# BASE
# =========================================================

class SupplierAvailabilityBase(BaseModel):
    supplier_product_id: int = Field(
        gt=0,
    )

    product_variant_id: int = Field(
        gt=0,
    )

    available_quantity: int = Field(
        default=0,
        ge=0,
    )

    status: AvailabilityStatus = (
        "AVAILABLE"
    )

    purchase_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )


# =========================================================
# CREATE
# =========================================================

class SupplierAvailabilityCreate(
    SupplierAvailabilityBase
):
    pass


# =========================================================
# UPDATE
# =========================================================

class SupplierAvailabilityUpdate(BaseModel):
    available_quantity: int | None = Field(
        default=None,
        ge=0,
    )

    status: AvailabilityStatus | None = None

    purchase_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )


# =========================================================
# RESPONSE
# =========================================================

class SupplierAvailabilityResponse(BaseModel):
    id: int

    supplier_product_id: int

    product_variant_id: int

    available_quantity: int

    status: AvailabilityStatus

    purchase_price: Decimal | None

    last_checked_at: datetime

    created_at: datetime

    updated_at: datetime

    supplier_product: AvailabilitySupplierProductSummary

    product_variant:AvailabilityVariantSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class SupplierAvailabilityListResponse(BaseModel):
    items: list[
        SupplierAvailabilityResponse
    ]

    page: int

    page_size: int

    total: int

    total_pages: int
from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# RESÚMENES
# =========================================================

class SupplierSummary(BaseModel):
    id: int

    name: str

    nit: str

    model_config = ConfigDict(
        from_attributes=True,
    )


class ProductSummary(BaseModel):
    id: int

    code: str

    name: str

    brand: str | None

    cover_image_url: str | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# BASE
# =========================================================

class SupplierProductBase(BaseModel):
    supplier_id: int = Field(
        gt=0,
    )

    product_id: int = Field(
        gt=0,
    )

    supplier_code: str | None = Field(
        default=None,
        max_length=80,
    )

    purchase_price: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    minimum_order_quantity: int = Field(
        default=1,
        ge=1,
    )

    lead_time_days: int = Field(
        default=0,
        ge=0,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# CREATE
# =========================================================

class SupplierProductCreate(
    SupplierProductBase
):
    pass


# =========================================================
# UPDATE
# =========================================================

class SupplierProductUpdate(BaseModel):
    supplier_code: str | None = Field(
        default=None,
        max_length=80,
    )

    purchase_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    minimum_order_quantity: int | None = Field(
        default=None,
        ge=1,
    )

    lead_time_days: int | None = Field(
        default=None,
        ge=0,
    )

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# RESPONSE
# =========================================================

class SupplierProductResponse(BaseModel):
    id: int

    supplier_id: int

    product_id: int

    supplier_code: str | None

    purchase_price: Decimal

    minimum_order_quantity: int

    lead_time_days: int

    is_active: bool

    created_at: datetime

    updated_at: datetime

    supplier: SupplierSummary

    product: ProductSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST
# =========================================================

class SupplierProductListResponse(BaseModel):
    items: list[
        SupplierProductResponse
    ]

    page: int

    page_size: int

    total: int

    total_pages: int
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# RESUMEN SUCURSAL
# =========================================================

class InventoryBranchSummary(BaseModel):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN TALLA
# =========================================================

class InventorySizeSummary(BaseModel):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN COLOR
# =========================================================

class InventoryColorSummary(BaseModel):
    id: int

    name: str

    hex_code: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN PRODUCTO
# =========================================================

class InventoryProductSummary(BaseModel):
    id: int

    code: str

    name: str

    brand: str | None = None

    cover_image_url: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# RESUMEN VARIANTE
# =========================================================

class InventoryVariantSummary(BaseModel):
    id: int

    product_id: int

    size_id: int

    color_id: int

    sku: str

    image_url: str | None = None

    is_active: bool

    size: InventorySizeSummary

    color: InventoryColorSummary

    product: InventoryProductSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CREATE
# =========================================================

class InventoryCreate(BaseModel):
    branch_id: int = Field(
        gt=0,
    )

    product_variant_id: int = Field(
        gt=0,
    )

    stock_quantity: int = Field(
        default=0,
        ge=0,
    )

    reserved_quantity: int = Field(
        default=0,
        ge=0,
    )

    minimum_stock: int = Field(
        default=0,
        ge=0,
    )

    maximum_stock: int | None = Field(
        default=None,
        ge=0,
    )

    reorder_point: int = Field(
        default=0,
        ge=0,
    )


# =========================================================
# UPDATE
# =========================================================

class InventoryUpdate(BaseModel):
    minimum_stock: int | None = Field(
        default=None,
        ge=0,
    )

    maximum_stock: int | None = Field(
        default=None,
        ge=0,
    )

    reorder_point: int | None = Field(
        default=None,
        ge=0,
    )

    is_active: bool | None = None


# =========================================================
# RESPONSE
# =========================================================

class InventoryResponse(BaseModel):
    id: int

    branch_id: int

    product_variant_id: int

    stock_quantity: int

    reserved_quantity: int

    available_quantity: int

    minimum_stock: int

    maximum_stock: int | None

    reorder_point: int

    is_low_stock: bool

    is_active: bool

    created_at: datetime

    updated_at: datetime

    branch: InventoryBranchSummary

    product_variant: InventoryVariantSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class InventoryListResponse(BaseModel):
    items: list[
        InventoryResponse
    ]

    page: int

    page_size: int

    total: int

    total_pages: int
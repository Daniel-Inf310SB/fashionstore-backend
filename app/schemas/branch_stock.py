from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
)


# =========================================================
# SUCURSAL
# =========================================================

class BranchStockBranchSummary(BaseModel):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PRODUCTO
# =========================================================

class BranchStockProductSummary(BaseModel):
    id: int

    code: str

    name: str

    brand: str | None = None

    cover_image_url: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# TALLA
# =========================================================

class BranchStockSizeSummary(BaseModel):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# COLOR
# =========================================================

class BranchStockColorSummary(BaseModel):
    id: int

    name: str

    hex_code: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# VARIANTE
# =========================================================

class BranchStockVariantSummary(BaseModel):
    id: int

    product_id: int

    sku: str

    image_url: str | None = None

    is_active: bool

    product: BranchStockProductSummary

    size: BranchStockSizeSummary

    color: BranchStockColorSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# ITEM EXISTENCIA
# =========================================================

class BranchStockItemResponse(BaseModel):
    inventory_id: int

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

    updated_at: datetime

    branch: BranchStockBranchSummary

    product_variant: BranchStockVariantSummary


# =========================================================
# RESUMEN
# =========================================================

class BranchStockSummaryResponse(BaseModel):
    total_records: int

    total_stock: int

    total_reserved: int

    total_available: int

    low_stock_records: int

    out_of_stock_records: int


# =========================================================
# LIST RESPONSE
# =========================================================

class BranchStockListResponse(BaseModel):
    items: list[
        BranchStockItemResponse
    ]

    summary:BranchStockSummaryResponse

    page: int

    page_size: int

    total: int

    total_pages: int
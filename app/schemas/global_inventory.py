from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
)


# =========================================================
# PRODUCTO
# =========================================================

class GlobalInventoryProductSummary(BaseModel):
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

class GlobalInventorySizeSummary(BaseModel):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# COLOR
# =========================================================

class GlobalInventoryColorSummary(BaseModel):
    id: int

    name: str

    hex_code: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# VARIANTE
# =========================================================

class GlobalInventoryVariantSummary(BaseModel):
    id: int

    product_id: int

    size_id: int

    color_id: int

    sku: str

    image_url: str | None = None

    is_active: bool

    product:GlobalInventoryProductSummary

    size:GlobalInventorySizeSummary

    color:GlobalInventoryColorSummary

    model_config = ConfigDict(
        from_attributes=True,)


# =========================================================
# ITEM GLOBAL
# =========================================================

class GlobalInventoryItem(BaseModel):
    product_variant_id: int

    branch_count: int

    total_stock: int

    total_reserved: int

    total_available: int

    low_stock_branches: int

    out_of_stock_branches: int

    is_low_stock: bool

    is_out_of_stock: bool

    last_updated_at:datetime | None

    product_variant: GlobalInventoryVariantSummary


# =========================================================
# RESUMEN GENERAL
# =========================================================

class GlobalInventorySummary(BaseModel):
    total_variants: int

    total_stock: int

    total_reserved: int

    total_available: int

    low_stock_variants: int

    out_of_stock_variants: int

    low_stock_branch_records: int

    out_of_stock_branch_records: int


# =========================================================
# LIST RESPONSE
# =========================================================

class GlobalInventoryListResponse(BaseModel):
    items: list[
        GlobalInventoryItem
    ]

    summary: GlobalInventorySummary

    page: int

    page_size: int

    total: int

    total_pages: int
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
)


# =========================================================
# MÓDULO 6 - CATÁLOGO DEL CLIENTE
# =========================================================


# =========================================================
# CATEGORÍA
# =========================================================

class CustomerCatalogCategoryResponse(
    BaseModel
):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# AUDIENCIA
# =========================================================

class CustomerCatalogAudienceResponse(
    BaseModel
):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PRODUCTO DEL CATÁLOGO
# =========================================================

class CustomerCatalogProductResponse(
    BaseModel
):
    id: int

    code: str

    name: str

    description: str | None

    brand: str | None

    base_price: Decimal

    min_price: Decimal

    max_price: Decimal

    cover_image_url: str | None

    category_id: int

    audience_id: int

    category: CustomerCatalogCategoryResponse

    audience: CustomerCatalogAudienceResponse

    variant_count: int

    available_variants: int

    total_available: int

    has_stock: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LISTADO
# =========================================================

class CustomerCatalogListResponse(
    BaseModel
):
    items: list[
        CustomerCatalogProductResponse
    ]

    page: int

    page_size: int

    total: int

    total_pages: int
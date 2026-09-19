from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
)


# =========================================================
# MÓDULO 6 - CATÁLOGO DEL CLIENTE
# CU26 - CONSULTAR DETALLE DE PRENDA
# =========================================================


# =========================================================
# CATEGORÍA
# =========================================================

class CustomerProductCategoryResponse(
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

class CustomerProductAudienceResponse(
    BaseModel
):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# TALLA
# =========================================================

class CustomerProductSizeResponse(
    BaseModel
):
    id: int

    name: str

    description: str | None

    sort_order: int

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# COLOR
# =========================================================

class CustomerProductColorResponse(
    BaseModel
):
    id: int

    name: str

    hex_code: str | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# IMAGEN
# =========================================================

class CustomerProductImageResponse(
    BaseModel
):
    id: int

    image_url: str

    alt_text: str | None

    sort_order: int

    is_primary: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PROMOCIÓN APLICADA
# =========================================================

class CustomerProductPromotionResponse(
    BaseModel
):
    id: int
    name: str
    discount_type: str
    discount_value: Decimal

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# VARIANTE
# =========================================================

class CustomerProductVariantResponse(
    BaseModel
):
    id: int

    sku: str

    size_id: int

    color_id: int

    additional_price: Decimal

    original_price: Decimal

    final_price: Decimal

    image_url: str | None

    size: CustomerProductSizeResponse

    color: CustomerProductColorResponse

    total_available: int

    has_stock: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# DETALLE DEL PRODUCTO
# =========================================================

class CustomerProductDetailResponse(
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

    original_min_price: Decimal

    original_max_price: Decimal

    has_discount: bool

    promotion: CustomerProductPromotionResponse | None

    cover_image_url: str | None

    category_id: int

    audience_id: int

    category: CustomerProductCategoryResponse

    audience: CustomerProductAudienceResponse

    images: list[
        CustomerProductImageResponse
    ]

    variants: list[
        CustomerProductVariantResponse
    ]

    variant_count: int

    available_variants: int

    total_available: int

    has_stock: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU26 - DISPONIBILIDAD POR SUCURSAL
# =========================================================


# =========================================================
# SUCURSAL CON DISPONIBILIDAD
# =========================================================

class CustomerProductAvailabilityBranchResponse(
    BaseModel
):
    branch_id: int

    branch_name: str

    city_id: int

    city_name: str

    address: str

    phone: str | None

    available_quantity: int

    has_stock: bool


# =========================================================
# DISPONIBILIDAD DE VARIANTE
# =========================================================

class CustomerProductAvailabilityResponse(
    BaseModel
):
    product_id: int

    product_name: str

    variant_id: int

    sku: str

    size: CustomerProductSizeResponse

    color: CustomerProductColorResponse

    total_available: int

    available_branches: int

    branches: list[
        CustomerProductAvailabilityBranchResponse
    ]
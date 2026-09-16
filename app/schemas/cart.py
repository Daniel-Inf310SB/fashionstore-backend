from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


CartStatus = Literal[
    "ACTIVE",
    "CONVERTED",
    "ABANDONED",
]


# =========================================================
# CU32 - CLIENTE
# =========================================================

class CartCustomerResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    email: str
    phone: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU32 - SUCURSAL
# =========================================================

class CartBranchResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str | None = None
    city_id: int

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU32 - PRODUCTO
# =========================================================

class CartProductResponse(BaseModel):
    id: int
    code: str
    name: str
    brand: str | None = None
    cover_image_url: str | None = None
    base_price: Decimal

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU32 - TALLA
# =========================================================

class CartSizeResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU32 - COLOR
# =========================================================

class CartColorResponse(BaseModel):
    id: int
    name: str
    hex_code: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU32 - VARIANTE
# =========================================================

class CartVariantResponse(BaseModel):
    id: int
    sku: str
    product_id: int
    size_id: int
    color_id: int
    image_url: str | None = None
    additional_price: Decimal | None = None

    product: CartProductResponse
    size: CartSizeResponse
    color: CartColorResponse

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU32 - ITEM DEL CARRITO
# =========================================================

class CartItemResponse(BaseModel):
    id: int
    cart_id: int
    product_variant_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime
    product_variant: CartVariantResponse

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU32 - CARRITO
# =========================================================

class CartResponse(BaseModel):
    id: int
    cart_code: str
    customer_id: int
    branch_id: int | None = None
    status: CartStatus
    created_at: datetime
    updated_at: datetime
    total_items: int
    total_units: int
    total_amount: Decimal
    customer: CartCustomerResponse
    branch: CartBranchResponse | None = None
    items: list[CartItemResponse]

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU32 - LISTA PAGINADA / ADMINISTRACIÓN
# =========================================================

class CartListResponse(BaseModel):
    items: list[CartResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


# =========================================================
# CU32 - PETICIONES DEL CLIENTE
# =========================================================

class CartItemAddRequest(BaseModel):
    branch_id: int = Field(
        ...,
        ge=1,
    )
    product_variant_id: int = Field(
        ...,
        ge=1,
    )
    quantity: int = Field(
        default=1,
        ge=1,
        le=999,
    )


class CartItemQuantityUpdate(BaseModel):
    quantity: int = Field(
        ...,
        ge=1,
        le=999,
    )


class CartCountResponse(BaseModel):
    branch_id: int
    total_items: int
    total_units: int


class MyCartResponse(BaseModel):
    branch_id: int
    has_cart: bool
    total_items: int
    total_units: int
    total_amount: Decimal
    cart: CartResponse | None = None


class CartActionResponse(BaseModel):
    message: str
    cart: CartResponse


class CartClearResponse(BaseModel):
    message: str
    branch_id: int
    removed_items: int
    total_items: int = 0
    total_units: int = 0

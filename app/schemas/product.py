from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# CATEGORY
# =========================================================

class ProductCategoryResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# AUDIENCE
# =========================================================

class ProductAudienceResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# BASE
# =========================================================

class ProductBase(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=50,
    )

    name: str = Field(
        min_length=1,
        max_length=150,
    )

    description: str | None = None

    brand: str | None = Field(
        default=None,
        max_length=100,
    )

    base_price: Decimal = Field(
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    category_id: int = Field(
        gt=0,
    )

    audience_id: int = Field(
        gt=0,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# CREATE
# =========================================================

class ProductCreate(ProductBase):
    pass


# =========================================================
# UPDATE
# =========================================================

class ProductUpdate(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    description: str | None = None

    brand: str | None = Field(
        default=None,
        max_length=100,
    )

    base_price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    category_id: int | None = Field(
        default=None,
        gt=0,
    )

    audience_id: int | None = Field(
        default=None,
        gt=0,
    )

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# RESPONSE
# =========================================================

class ProductResponse(BaseModel):
    id: int

    code: str

    name: str

    description: str | None

    brand: str | None

    base_price: Decimal

    cover_image_url: str | None

    cover_image_public_id: str | None

    category_id: int

    audience_id: int

    is_active: bool

    created_at: datetime

    updated_at: datetime

    category: ProductCategoryResponse

    audience: ProductAudienceResponse

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class ProductListResponse(BaseModel):
    items: list[ProductResponse]

    page: int

    page_size: int

    total: int

    total_pages: int


# =========================================================
# COVER RESPONSE
# =========================================================

class ProductCoverResponse(BaseModel):
    id: int

    cover_image_url: str | None

    cover_image_public_id: str | None
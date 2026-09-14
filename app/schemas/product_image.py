from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ProductImageUpdate(BaseModel):
    alt_text: str | None = Field(
        default=None,
        max_length=255,
    )

    sort_order: int | None = Field(
        default=None,
        ge=0,
    )

    is_primary: bool | None = None

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class ProductImageResponse(BaseModel):
    id: int

    product_id: int

    image_url: str

    cloudinary_public_id: str | None

    alt_text: str | None

    sort_order: int

    is_primary: bool

    is_active: bool

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class ProductImageListResponse(BaseModel):
    items: list[ProductImageResponse]

    total: int
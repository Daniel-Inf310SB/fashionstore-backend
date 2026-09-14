from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# BASE
# =========================================================

class SizeBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=30,
    )

    description: str | None = Field(
        default=None,
        max_length=150,
    )

    sort_order: int = Field(
        default=0,
        ge=0,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# CREATE
# =========================================================

class SizeCreate(SizeBase):
    pass


# =========================================================
# UPDATE
# =========================================================

class SizeUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

    description: str | None = Field(
        default=None,
        max_length=150,
    )

    sort_order: int | None = Field(
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

class SizeResponse(BaseModel):
    id: int

    name: str

    description: str | None

    sort_order: int

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class SizeListResponse(BaseModel):
    items: list[SizeResponse]

    page: int

    page_size: int

    total: int

    total_pages: int
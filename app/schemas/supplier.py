from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# BASE
# =========================================================

class SupplierBase(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=120,
    )

    business_name: str | None = Field(
        default=None,
        max_length=160,
    )

    nit: str = Field(
        min_length=3,
        max_length=40,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    email: str | None = Field(
        default=None,
        max_length=160,
    )

    address: str | None = Field(
        default=None,
        max_length=255,
    )

    contact_name: str | None = Field(
        default=None,
        max_length=120,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# CREATE
# =========================================================

class SupplierCreate(SupplierBase):
    pass


# =========================================================
# UPDATE
# =========================================================

class SupplierUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )

    business_name: str | None = Field(
        default=None,
        max_length=160,
    )

    nit: str | None = Field(
        default=None,
        min_length=3,
        max_length=40,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    email: str | None = Field(
        default=None,
        max_length=160,
    )

    address: str | None = Field(
        default=None,
        max_length=255,
    )

    contact_name: str | None = Field(
        default=None,
        max_length=120,
    )

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# RESPONSE
# =========================================================

class SupplierResponse(BaseModel):
    id: int

    name: str

    business_name: str | None

    nit: str

    phone: str | None

    email: str | None

    address: str | None

    contact_name: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]

    page: int

    page_size: int

    total: int

    total_pages: int

from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# CITY SUMMARY
# =========================================================

class BranchCitySummary(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# BASE
# =========================================================

class BranchBase(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=150,
    )

    address: str = Field(
        min_length=2,
        max_length=255,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    latitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-90"),
        le=Decimal("90"),
    )

    longitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-180"),
        le=Decimal("180"),
    )

    city_id: int = Field(
        gt=0,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# CREATE
# =========================================================

class BranchCreate(BranchBase):
    pass


# =========================================================
# UPDATE
# =========================================================

class BranchUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    address: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    latitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-90"),
        le=Decimal("90"),
    )

    longitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-180"),
        le=Decimal("180"),
    )

    city_id: int | None = Field(
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

class BranchResponse(BaseModel):
    id: int

    name: str

    address: str

    phone: str | None

    latitude: Decimal | None

    longitude: Decimal | None

    city_id: int

    city: BranchCitySummary

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class BranchListResponse(BaseModel):
    items: list[BranchResponse]

    page: int

    page_size: int

    total: int

    total_pages: int
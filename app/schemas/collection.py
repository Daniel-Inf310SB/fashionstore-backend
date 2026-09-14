from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class CollectionBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=120,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    launch_date: date | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    launch_date: date | None = None

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class CollectionResponse(BaseModel):
    id: int

    name: str

    description: str | None

    launch_date: date | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class CollectionListResponse(BaseModel):
    items: list[CollectionResponse]

    page: int

    page_size: int

    total: int

    total_pages: int
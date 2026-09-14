from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CityBase(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
        examples=["Santa Cruz"],
    )


class CityCreate(CityBase):
    pass


class CityUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    is_active: bool | None = None


class CityResponse(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CityListResponse(BaseModel):
    items: list[CityResponse]

    page: int
    page_size: int
    total: int
    total_pages: int
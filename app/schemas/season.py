from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class SeasonBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    start_date: date | None = None

    end_date: date | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError(
                "La fecha final no puede ser anterior a la fecha inicial."
            )

        return self


class SeasonCreate(SeasonBase):
    pass


class SeasonUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    start_date: date | None = None

    end_date: date | None = None

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class SeasonResponse(BaseModel):
    id: int

    name: str

    description: str | None

    start_date: date | None

    end_date: date | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class SeasonListResponse(BaseModel):
    items: list[SeasonResponse]

    page: int

    page_size: int

    total: int

    total_pages: int
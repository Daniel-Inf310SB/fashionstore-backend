from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


DISCOUNT_TYPES = {
    "PERCENTAGE",
    "FIXED",
}


class PromotionBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=120,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    discount_type: str = Field(
        min_length=1,
        max_length=20,
    )

    discount_value: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
    )

    start_at: datetime

    end_at: datetime

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(
        cls,
        value: str,
    ) -> str:

        clean_value = (
            value.strip().upper()
        )

        if clean_value not in DISCOUNT_TYPES:
            raise ValueError(
                "El tipo de descuento debe ser "
                "PERCENTAGE o FIXED."
            )

        return clean_value

    @model_validator(mode="after")
    def validate_promotion(self):

        if self.end_at <= self.start_at:
            raise ValueError(
                "La fecha final debe ser posterior "
                "a la fecha inicial."
            )

        if (
            self.discount_type == "PERCENTAGE"
            and self.discount_value > Decimal("100")
        ):
            raise ValueError(
                "El descuento porcentual "
                "no puede ser mayor a 100."
            )

        return self


class PromotionCreate(PromotionBase):
    pass


class PromotionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    discount_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    discount_value: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )

    start_at: datetime | None = None

    end_at: datetime | None = None

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        clean_value = (
            value.strip().upper()
        )

        if clean_value not in DISCOUNT_TYPES:
            raise ValueError(
                "El tipo de descuento debe ser "
                "PERCENTAGE o FIXED."
            )

        return clean_value


class PromotionResponse(BaseModel):
    id: int

    name: str

    description: str | None

    discount_type: str

    discount_value: Decimal

    start_at: datetime

    end_at: datetime

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class PromotionListResponse(BaseModel):
    items: list[PromotionResponse]

    page: int

    page_size: int

    total: int

    total_pages: int
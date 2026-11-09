"""Contratos JSON para banners administrables y escaparate móvil."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator, field_validator


class HomeBannerInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    subtitle: str | None = Field(default=None, max_length=250)
    image_url: HttpUrl
    mobile_image_url: HttpUrl | None = None
    target_type: Literal["catalog", "product", "category", "collection", "promotion"] = "catalog"
    target_id: int | None = Field(default=None, ge=1)
    sort_order: int = Field(default=0, ge=0, le=100000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    show_as_popup: bool = False
    popup_priority: int = Field(default=0, ge=0, le=100000)
    is_active: bool = True

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_timezone(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Las fechas de campaña deben llevar zona horaria.")
        return value

    @field_validator("image_url", "mobile_image_url")
    @classmethod
    def require_storable_url(cls, value):
        if value is not None and len(str(value)) > 500:
            raise ValueError("La URL de imagen no puede superar 500 caracteres.")
        return value

    @model_validator(mode="after")
    def check_target_and_dates(self):
        if (self.target_type == "catalog") != (self.target_id is None):
            raise ValueError("El destino catalog no tiene ID; los otros destinos requieren target_id.")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at debe ser posterior a starts_at.")
        return self


class HomeBannerPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    subtitle: str | None = Field(default=None, max_length=250)
    image_url: HttpUrl | None = None
    mobile_image_url: HttpUrl | None = None
    target_type: Literal["catalog", "product", "category", "collection", "promotion"] | None = None
    target_id: int | None = Field(default=None, ge=1)
    sort_order: int | None = Field(default=None, ge=0, le=100000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    show_as_popup: bool | None = None
    popup_priority: int | None = Field(default=None, ge=0, le=100000)
    is_active: bool | None = None


class HomeBannerOut(BaseModel):
    id: int
    title: str
    subtitle: str | None
    image_url: str
    mobile_image_url: str | None
    target_type: str
    target_id: int | None
    sort_order: int
    starts_at: datetime | None
    ends_at: datetime | None
    show_as_popup: bool
    popup_priority: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

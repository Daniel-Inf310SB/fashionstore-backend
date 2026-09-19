from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.customer_catalog import CustomerCatalogProductResponse


class StorePromotionResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    discount_type: str
    discount_value: Decimal
    start_at: datetime
    end_at: datetime
    product_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class StoreCollectionResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    launch_date: date | None = None
    product_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class StoreSeasonResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    product_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class StorePromotionListResponse(BaseModel):
    items: list[StorePromotionResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class StoreCollectionListResponse(BaseModel):
    items: list[StoreCollectionResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class StoreSeasonListResponse(BaseModel):
    items: list[StoreSeasonResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class StoreMerchandisingProductsResponse(BaseModel):
    merchandising_id: int
    merchandising_type: str
    name: str
    description: str | None = None
    items: list[CustomerCatalogProductResponse]
    page: int
    page_size: int
    total: int
    total_pages: int

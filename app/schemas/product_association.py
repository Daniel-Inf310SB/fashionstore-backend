from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# CREAR ASOCIACIONES
# =========================================================

class ProductSeasonCreate(BaseModel):
    season_id: int = Field(gt=0)


class ProductCollectionCreate(BaseModel):
    collection_id: int = Field(gt=0)


class ProductPromotionCreate(BaseModel):
    promotion_id: int = Field(gt=0)


# =========================================================
# RESPUESTAS BÁSICAS
# =========================================================

class SeasonAssociationData(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


class CollectionAssociationData(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


class PromotionAssociationData(BaseModel):
    id: int
    name: str
    discount_type: str
    discount_value: float
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PRODUCT SEASON
# =========================================================

class ProductSeasonResponse(BaseModel):
    id: int
    product_id: int
    season_id: int
    created_at: datetime

    season: SeasonAssociationData

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PRODUCT COLLECTION
# =========================================================

class ProductCollectionResponse(BaseModel):
    id: int
    product_id: int
    collection_id: int
    created_at: datetime

    collection: CollectionAssociationData

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PRODUCT PROMOTION
# =========================================================

class ProductPromotionResponse(BaseModel):
    id: int
    product_id: int
    promotion_id: int
    created_at: datetime

    promotion: PromotionAssociationData

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# TODAS LAS ASOCIACIONES
# =========================================================

class ProductAssociationsResponse(BaseModel):
    seasons: list[ProductSeasonResponse]

    collections: list[ProductCollectionResponse]

    promotions: list[ProductPromotionResponse]
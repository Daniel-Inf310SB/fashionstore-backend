from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.customer_merchandising import (
    StoreCollectionListResponse,
    StoreMerchandisingProductsResponse,
    StorePromotionListResponse,
    StoreSeasonListResponse,
)
from app.services.customer_merchandising import CustomerMerchandisingService


router = APIRouter(prefix="/store", tags=["Store - Merchandising"])


@router.get("/promotions", response_model=StorePromotionListResponse)
def get_store_promotions(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
):
    return CustomerMerchandisingService.get_active_promotions(
        db, page=page, page_size=page_size, search=search
    )


@router.get("/collections", response_model=StoreCollectionListResponse)
def get_store_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
):
    return CustomerMerchandisingService.get_active_collections(
        db, page=page, page_size=page_size, search=search
    )


@router.get("/seasons", response_model=StoreSeasonListResponse)
def get_store_seasons(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
):
    return CustomerMerchandisingService.get_active_seasons(
        db, page=page, page_size=page_size, search=search
    )


def _products(
    merchandising_type: Literal["promotion", "collection", "season"],
    merchandising_id: int,
    page: int,
    page_size: int,
    branch_id: int | None,
    search: str | None,
    audience: str | None,
    category: str | None,
    size_id: int | None,
    color_id: int | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    in_stock: bool | None,
    sort_by: Literal["name", "price", "created_at"],
    sort_order: Literal["asc", "desc"],
    db: Session,
):
    try:
        return CustomerMerchandisingService.get_products(
            db,
            merchandising_type=merchandising_type,
            merchandising_id=merchandising_id,
            page=page,
            page_size=page_size,
            branch_id=branch_id,
            search=search,
            audience=audience,
            category=category,
            size_id=size_id,
            color_id=color_id,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/promotions/{promotion_id}/products", response_model=StoreMerchandisingProductsResponse)
def get_promotion_products(
    promotion_id: int,
    page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=100),
    branch_id: int | None = Query(None, ge=1), search: str | None = Query(None, max_length=150),
    audience: str | None = Query(None, max_length=50), category: str | None = Query(None, max_length=100),
    size_id: int | None = Query(None, ge=1), color_id: int | None = Query(None, ge=1),
    min_price: Decimal | None = Query(None, ge=0), max_price: Decimal | None = Query(None, ge=0),
    in_stock: bool | None = Query(None),
    sort_by: Literal["name", "price", "created_at"] = Query("name"),
    sort_order: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
):
    return _products("promotion", promotion_id, page, page_size, branch_id, search, audience, category, size_id, color_id, min_price, max_price, in_stock, sort_by, sort_order, db)


@router.get("/collections/{collection_id}/products", response_model=StoreMerchandisingProductsResponse)
def get_collection_products(
    collection_id: int,
    page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=100),
    branch_id: int | None = Query(None, ge=1), search: str | None = Query(None, max_length=150),
    audience: str | None = Query(None, max_length=50), category: str | None = Query(None, max_length=100),
    size_id: int | None = Query(None, ge=1), color_id: int | None = Query(None, ge=1),
    min_price: Decimal | None = Query(None, ge=0), max_price: Decimal | None = Query(None, ge=0),
    in_stock: bool | None = Query(None),
    sort_by: Literal["name", "price", "created_at"] = Query("name"),
    sort_order: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
):
    return _products("collection", collection_id, page, page_size, branch_id, search, audience, category, size_id, color_id, min_price, max_price, in_stock, sort_by, sort_order, db)


@router.get("/seasons/{season_id}/products", response_model=StoreMerchandisingProductsResponse)
def get_season_products(
    season_id: int,
    page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=100),
    branch_id: int | None = Query(None, ge=1), search: str | None = Query(None, max_length=150),
    audience: str | None = Query(None, max_length=50), category: str | None = Query(None, max_length=100),
    size_id: int | None = Query(None, ge=1), color_id: int | None = Query(None, ge=1),
    min_price: Decimal | None = Query(None, ge=0), max_price: Decimal | None = Query(None, ge=0),
    in_stock: bool | None = Query(None),
    sort_by: Literal["name", "price", "created_at"] = Query("name"),
    sort_order: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
):
    return _products("season", season_id, page, page_size, branch_id, search, audience, category, size_id, color_id, min_price, max_price, in_stock, sort_by, sort_order, db)

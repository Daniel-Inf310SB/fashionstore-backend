from __future__ import annotations

import math
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.collection import Collection
from app.models.product import Product
from app.models.product_collection import ProductCollection
from app.models.product_promotion import ProductPromotion
from app.models.product_season import ProductSeason
from app.models.promotion import Promotion
from app.models.season import Season
from app.services.customer_catalog import CustomerCatalogService


class CustomerMerchandisingService:
    @staticmethod
    def _page(page: int, page_size: int) -> tuple[int, int]:
        return max(1, page), max(1, min(page_size, 100))

    @staticmethod
    def _total_pages(total: int, page_size: int) -> int:
        return math.ceil(total / page_size) if total > 0 else 0

    @staticmethod
    def get_active_promotions(
        db: Session,
        *,
        page: int = 1,
        page_size: int = 12,
        search: str | None = None,
    ) -> dict:
        page, page_size = CustomerMerchandisingService._page(page, page_size)
        now = datetime.now(timezone.utc)

        query = db.query(Promotion).filter(
            Promotion.is_active.is_(True),
            Promotion.start_at <= now,
            Promotion.end_at >= now,
        )

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Promotion.name.ilike(pattern), Promotion.description.ilike(pattern)))

        total = query.count()
        rows = (
            query.order_by(Promotion.start_at.desc(), Promotion.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = []
        for row in rows:
            product_count = (
                db.query(func.count(func.distinct(ProductPromotion.product_id)))
                .join(Product, ProductPromotion.product_id == Product.id)
                .filter(
                    ProductPromotion.promotion_id == row.id,
                    Product.is_active.is_(True),
                )
                .scalar()
                or 0
            )
            items.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "discount_type": row.discount_type,
                "discount_value": row.discount_value,
                "start_at": row.start_at,
                "end_at": row.end_at,
                "product_count": int(product_count),
            })

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": CustomerMerchandisingService._total_pages(total, page_size),
        }

    @staticmethod
    def get_active_collections(
        db: Session,
        *,
        page: int = 1,
        page_size: int = 12,
        search: str | None = None,
    ) -> dict:
        page, page_size = CustomerMerchandisingService._page(page, page_size)
        today = date.today()

        query = db.query(Collection).filter(Collection.is_active.is_(True))
        # A future collection remains hidden from the public Store until launch day.
        query = query.filter(or_(Collection.launch_date.is_(None), Collection.launch_date <= today))

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Collection.name.ilike(pattern), Collection.description.ilike(pattern)))

        total = query.count()
        rows = (
            query.order_by(Collection.launch_date.desc().nullslast(), Collection.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = []
        for row in rows:
            product_count = (
                db.query(func.count(func.distinct(ProductCollection.product_id)))
                .join(Product, ProductCollection.product_id == Product.id)
                .filter(ProductCollection.collection_id == row.id, Product.is_active.is_(True))
                .scalar()
                or 0
            )
            items.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "launch_date": row.launch_date,
                "product_count": int(product_count),
            })

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": CustomerMerchandisingService._total_pages(total, page_size),
        }

    @staticmethod
    def get_active_seasons(
        db: Session,
        *,
        page: int = 1,
        page_size: int = 12,
        search: str | None = None,
    ) -> dict:
        page, page_size = CustomerMerchandisingService._page(page, page_size)
        today = date.today()

        query = db.query(Season).filter(
            Season.is_active.is_(True),
            or_(Season.start_date.is_(None), Season.start_date <= today),
            or_(Season.end_date.is_(None), Season.end_date >= today),
        )

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Season.name.ilike(pattern), Season.description.ilike(pattern)))

        total = query.count()
        rows = (
            query.order_by(Season.start_date.desc().nullslast(), Season.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = []
        for row in rows:
            product_count = (
                db.query(func.count(func.distinct(ProductSeason.product_id)))
                .join(Product, ProductSeason.product_id == Product.id)
                .filter(ProductSeason.season_id == row.id, Product.is_active.is_(True))
                .scalar()
                or 0
            )
            items.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "start_date": row.start_date,
                "end_date": row.end_date,
                "product_count": int(product_count),
            })

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": CustomerMerchandisingService._total_pages(total, page_size),
        }

    @staticmethod
    def get_products(
        db: Session,
        *,
        merchandising_type: Literal["promotion", "collection", "season"],
        merchandising_id: int,
        page: int = 1,
        page_size: int = 12,
        branch_id: int | None = None,
        search: str | None = None,
        audience: str | None = None,
        category: str | None = None,
        size_id: int | None = None,
        color_id: int | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        in_stock: bool | None = None,
        sort_by: Literal["name", "price", "created_at"] = "name",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> dict:
        today = date.today()
        now = datetime.now(timezone.utc)

        promotion_id = None
        collection_id = None
        season_id = None

        if merchandising_type == "promotion":
            row = db.query(Promotion).filter(
                Promotion.id == merchandising_id,
                Promotion.is_active.is_(True),
                Promotion.start_at <= now,
                Promotion.end_at >= now,
            ).first()
            promotion_id = merchandising_id
        elif merchandising_type == "collection":
            row = db.query(Collection).filter(
                Collection.id == merchandising_id,
                Collection.is_active.is_(True),
                or_(Collection.launch_date.is_(None), Collection.launch_date <= today),
            ).first()
            collection_id = merchandising_id
        else:
            row = db.query(Season).filter(
                Season.id == merchandising_id,
                Season.is_active.is_(True),
                or_(Season.start_date.is_(None), Season.start_date <= today),
                or_(Season.end_date.is_(None), Season.end_date >= today),
            ).first()
            season_id = merchandising_id

        if row is None:
            raise LookupError("El recurso solicitado no está disponible actualmente en la tienda.")

        catalog = CustomerCatalogService.get_catalog(
            db=db,
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
            promotion=None,
            promotion_id=promotion_id,
            collection_id=collection_id,
            season_id=season_id,
            in_stock=in_stock,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {
            "merchandising_id": row.id,
            "merchandising_type": merchandising_type,
            "name": row.name,
            "description": row.description,
            **catalog,
        }

"""Composición del inicio público; reutiliza reglas existentes del catálogo."""
from datetime import datetime, timezone
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.category import Category
from app.models.collection import Collection
from app.models.home_banner import HomeBanner
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.promotion import Promotion
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.inventory import Inventory
from app.services.customer_catalog import CustomerCatalogService
from app.services.customer_merchandising import CustomerMerchandisingService


class StoreHomeService:
    @staticmethod
    def check_branch(db: Session, tenant_id: int, branch_id: int):
        if not db.query(Branch.id).filter(
            Branch.id == branch_id, Branch.tenant_id == tenant_id, Branch.is_active.is_(True)
        ).first():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Sucursal no disponible para esta empresa.")

    @staticmethod
    def banners(db: Session, tenant_id: int):
        now = datetime.now(timezone.utc)
        return db.query(HomeBanner).filter(
            HomeBanner.tenant_id == tenant_id,
            HomeBanner.is_active.is_(True),
            or_(HomeBanner.starts_at.is_(None), HomeBanner.starts_at <= now),
            or_(HomeBanner.ends_at.is_(None), HomeBanner.ends_at > now),
        ).order_by(HomeBanner.sort_order, HomeBanner.id).limit(12).all()

    @staticmethod
    def products(db: Session, tenant_id: int, branch_id: int, *, limit=8, **filters):
        result = CustomerCatalogService.get_catalog(
            db=db, tenant_id=tenant_id, branch_id=branch_id,
            page=1, page_size=limit, in_stock=True, **filters,
        )
        return result["items"]

    @staticmethod
    def best_sellers(db: Session, tenant_id: int, branch_id: int, limit: int = 8):
        # Únicamente ventas de contado pagadas de la propia sucursal.
        rows = db.query(
            Product.id.label("product_id"),
            Product.name.label("name"),
            Product.cover_image_url.label("cover_image_url"),
            func.sum(SaleItem.quantity).label("units_sold"),
        ).join(ProductVariant, ProductVariant.product_id == Product.id).join(
            SaleItem, SaleItem.product_variant_id == ProductVariant.id
        ).join(Sale, Sale.id == SaleItem.sale_id).join(
            Inventory, Inventory.product_variant_id == ProductVariant.id
        ).filter(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True), ProductVariant.is_active.is_(True),
            Sale.tenant_id == tenant_id, Sale.branch_id == branch_id, Sale.status == "PAID",
            Inventory.branch_id == branch_id, Inventory.is_active.is_(True),
            Inventory.stock_quantity > Inventory.reserved_quantity,
        ).group_by(Product.id, Product.name, Product.cover_image_url).order_by(
            func.sum(SaleItem.quantity).desc(), Product.id.asc()
        ).limit(limit).all()
        return [
            {"product_id": item.product_id, "name": item.name,
             "cover_image_url": item.cover_image_url, "units_sold": int(item.units_sold)}
            for item in rows
        ]

    @classmethod
    def home(cls, db: Session, tenant, branch_id: int):
        cls.check_branch(db, tenant.id, branch_id)
        facets = cls._facets(db, tenant.id, branch_id)
        promotions = CustomerMerchandisingService.get_active_promotions(
            db, page=1, page_size=6, search=None, tenant_id=tenant.id
        )["items"]
        collections = CustomerMerchandisingService.get_active_collections(
            db, page=1, page_size=6, search=None, tenant_id=tenant.id
        )["items"]
        return {
            "tenant": {"id": tenant.id, "slug": tenant.slug, "name": tenant.name},
            "branch_id": branch_id,
            "banners": cls.banners(db, tenant.id),
            "categories": facets,
            "promotions": promotions,
            "featured_collections": collections,
            "offers": cls.products(db, tenant.id, branch_id, limit=8, promotion=True),
            "new_arrivals": cls.products(db, tenant.id, branch_id, limit=8,
                                         sort_by="created_at", sort_order="desc"),
            "best_sellers": cls.best_sellers(db, tenant.id, branch_id),
            "recommended": cls.products(db, tenant.id, branch_id, limit=8,
                                        sort_by="name", sort_order="asc"),
        }

    @staticmethod
    def _facets(db: Session, tenant_id: int, branch_id: int):
        # Solo categorías realmente utilizadas por prendas activas con inventario en la sucursal.
        from app.models.inventory import Inventory
        rows = db.query(Category.id, Category.name, func.count(func.distinct(Product.id))).join(
            Product, Product.category_id == Category.id
        ).join(ProductVariant, ProductVariant.product_id == Product.id).join(
            Inventory, Inventory.product_variant_id == ProductVariant.id
        ).filter(
            Product.tenant_id == tenant_id, Product.is_active.is_(True),
            Category.is_active.is_(True), Category.tenant_id == tenant_id, ProductVariant.is_active.is_(True),
            Inventory.branch_id == branch_id, Inventory.is_active.is_(True),
        ).group_by(Category.id, Category.name).order_by(Category.name).limit(12).all()
        return [{"id": id, "name": name, "product_count": count} for id, name, count in rows]

    @staticmethod
    def validate_destination(db: Session, tenant_id: int, target_type: str, target_id: int | None):
        from fastapi import HTTPException
        if target_type == "catalog":
            if target_id is not None:
                raise HTTPException(422, "Un banner de catálogo no tiene target_id.")
            return
        model = {"product": Product, "category": Category,
                 "collection": Collection, "promotion": Promotion}.get(target_type)
        if model is None or target_id is None:
            raise HTTPException(422, "Destino inválido.")
        query = db.query(model.id).filter(model.id == target_id, model.is_active.is_(True))
        if target_type == "category":
            query = query.filter(model.tenant_id == tenant_id).filter(db.query(Product.id).filter(
                Product.category_id == target_id, Product.tenant_id == tenant_id,
                Product.is_active.is_(True)
            ).exists())
        else:
            query = query.filter(model.tenant_id == tenant_id)
        if not query.first():
            raise HTTPException(422, "Destino inexistente o ajeno a la empresa.")

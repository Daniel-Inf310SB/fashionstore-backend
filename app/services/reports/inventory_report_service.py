from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.inventory import Inventory
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.reports import InventoryReportFilters
from app.services.reports.base import money, report_payload


class InventoryReportService:
    COLUMNS = [
        {"key": "branch", "label": "Sucursal"},
        {"key": "product", "label": "Producto"},
        {"key": "category", "label": "Categoría"},
        {"key": "sku", "label": "SKU"},
        {"key": "size", "label": "Talla"},
        {"key": "color", "label": "Color"},
        {"key": "stock", "label": "Stock físico"},
        {"key": "reserved", "label": "Reservado"},
        {"key": "available", "label": "Disponible"},
        {"key": "minimum", "label": "Mínimo"},
        {"key": "reorder_point", "label": "Punto reposición"},
        {"key": "stock_state", "label": "Estado stock"},
    ]

    @staticmethod
    def _state(inv: Inventory) -> str:
        available = inv.stock_quantity - inv.reserved_quantity
        if available <= 0:
            return "OUT_OF_STOCK"
        if available <= inv.reorder_point:
            return "LOW_STOCK"
        return "IN_STOCK"

    @staticmethod
    def build(db: Session, filters: InventoryReportFilters) -> dict:
        stmt = (
            select(Inventory)
            .join(ProductVariant, ProductVariant.id == Inventory.product_variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .options(
                joinedload(Inventory.branch),
                joinedload(Inventory.product_variant).joinedload(ProductVariant.size),
                joinedload(Inventory.product_variant).joinedload(ProductVariant.color),
                joinedload(Inventory.product_variant)
                .joinedload(ProductVariant.product)
                .joinedload(Product.category),
            )
        )

        if filters.branch_id:
            stmt = stmt.where(Inventory.branch_id == filters.branch_id)
        if filters.product_id:
            stmt = stmt.where(Product.id == filters.product_id)
        if filters.category_id:
            stmt = stmt.where(Product.category_id == filters.category_id)
        if filters.audience_id:
            stmt = stmt.where(Product.audience_id == filters.audience_id)
        if filters.size_id:
            stmt = stmt.where(ProductVariant.size_id == filters.size_id)
        if filters.color_id:
            stmt = stmt.where(ProductVariant.color_id == filters.color_id)
        if filters.is_active is not None:
            stmt = stmt.where(Inventory.is_active == filters.is_active)
        if filters.min_stock is not None:
            stmt = stmt.where(Inventory.stock_quantity >= filters.min_stock)
        if filters.max_stock is not None:
            stmt = stmt.where(Inventory.stock_quantity <= filters.max_stock)
        if filters.search and filters.search.strip():
            term = f"%{filters.search.strip()}%"
            stmt = stmt.where(or_(Product.name.ilike(term), Product.code.ilike(term), ProductVariant.sku.ilike(term)))

        inventories = db.scalars(stmt.order_by(Product.name, ProductVariant.sku)).unique().all()

        rows: list[dict] = []
        total_stock = 0
        total_reserved = 0
        total_available = 0
        low_stock = 0
        out_of_stock = 0

        for inv in inventories:
            state = InventoryReportService._state(inv)
            if filters.stock_state and state != filters.stock_state:
                continue

            available = inv.stock_quantity - inv.reserved_quantity
            variant = inv.product_variant
            product = variant.product

            if state == "LOW_STOCK":
                low_stock += 1
            elif state == "OUT_OF_STOCK":
                out_of_stock += 1

            total_stock += inv.stock_quantity
            total_reserved += inv.reserved_quantity
            total_available += available

            rows.append(
                {
                    "branch": inv.branch.name if inv.branch else "—",
                    "product": product.name,
                    "category": product.category.name if product.category else "—",
                    "sku": variant.sku,
                    "size": variant.size.name if variant.size else "—",
                    "color": variant.color.name if variant.color else "—",
                    "stock": inv.stock_quantity,
                    "reserved": inv.reserved_quantity,
                    "available": available,
                    "minimum": inv.minimum_stock,
                    "reorder_point": inv.reorder_point,
                    "stock_state": state,
                }
            )

        summary = {
            "variants_count": len(rows),
            "stock_total": total_stock,
            "reserved_total": total_reserved,
            "available_total": total_available,
            "low_stock_count": low_stock,
            "out_of_stock_count": out_of_stock,
        }

        return report_payload(
            report_key="inventory",
            title="Reporte de inventario",
            filters=filters,
            summary=summary,
            columns=InventoryReportService.COLUMNS,
            rows=rows,
        )

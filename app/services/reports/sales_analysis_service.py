"""Consultas analíticas de ventas autorizadas, sin SQL generado por el LLM."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.product_variant import ProductVariant
from app.models.product import Product
from app.schemas.reports import SalesReportFilters
from app.services.reports.base import money, report_payload
from app.services.reports.sales_report_service import SalesReportService

ANALYSES = {"top_products", "branch_comparison", "weekly_sales", "category_revenue"}
TITLES = {
    "top_products": "Productos más vendidos",
    "branch_comparison": "Comparación de ventas por sucursal",
    "weekly_sales": "Ventas agrupadas por semana",
    "category_revenue": "Ingresos por categoría",
}

class SalesAnalysisService:
    @staticmethod
    def build(db: Session, filters: SalesReportFilters, *, tenant_id: int, kind: str, limit: int = 10) -> dict:
        if kind not in ANALYSES:
            raise ValueError("Tipo de análisis no soportado.")
        # Filtrado consolidado del reporte existente: incluye tenant, fechas,
        # clientes, productos, categorías, métodos, estados y montos.
        original = SalesReportService.build(db, filters, tenant_id=tenant_id)
        codes = [row["sale_code"] for row in original["rows"]]
        aggregates: dict[str, dict] = defaultdict(lambda: {"units": 0, "total": Decimal("0"), "sales": set()})
        if codes:
            stmt = (select(Sale).where(Sale.tenant_id == tenant_id, Sale.sale_code.in_(codes))
                    .options(joinedload(Sale.branch), selectinload(Sale.items)
                             .joinedload(SaleItem.product_variant)
                             .joinedload(ProductVariant.product)
                             .joinedload(Product.category)))
            for sale in db.scalars(stmt).unique().all():
                if kind == "branch_comparison":
                    labels = [(sale.branch.name if sale.branch else "Sin sucursal", sum(item.quantity for item in sale.items), Decimal(str(sale.total_amount)))]
                elif kind == "weekly_sales":
                    week = sale.created_at.date() - timedelta(days=sale.created_at.weekday())
                    labels = [(week.isoformat(), sum(item.quantity for item in sale.items), Decimal(str(sale.total_amount)))]
                else:
                    labels = []
                    for item in sale.items:
                        product = item.product_variant.product if item.product_variant else None
                        if not product:
                            continue
                        # Si se filtró por artículo/categoría/audiencia, no sumar
                        # partidas ajenas al filtro (aunque la venta coincidiera).
                        if filters.product_id and product.id != filters.product_id:
                            continue
                        if filters.category_id and product.category_id != filters.category_id:
                            continue
                        if filters.audience_id and product.audience_id != filters.audience_id:
                            continue
                        label = product.name if kind == "top_products" else (product.category.name if product.category else "Sin categoría")
                        labels.append((label, item.quantity, Decimal(str(item.subtotal))))
                for label, qty, amount in labels:
                    current = aggregates[label]
                    current["units"] += qty
                    current["total"] += amount
                    current["sales"].add(sale.id)
        order = (lambda pair: (-pair[1]["units"], -pair[1]["total"], pair[0])) if kind == "top_products" else (lambda pair: (-pair[1]["total"], pair[0]))
        sorted_items = sorted(aggregates.items(), key=order)
        if kind == "weekly_sales":
            sorted_items = sorted(aggregates.items())
        if kind == "top_products":
            sorted_items = sorted_items[:limit]
        label_key = {"top_products":"product", "branch_comparison":"branch", "weekly_sales":"week", "category_revenue":"category"}[kind]
        rows = [{label_key: label, "sales_count": len(a["sales"]), "units": a["units"], "total": money(a["total"])} for label,a in sorted_items]
        columns = [{"key":label_key,"label":{"product":"Producto", "branch":"Sucursal", "week":"Semana desde", "category":"Categoría"}[label_key]},
                   {"key":"sales_count","label":"Ventas"}, {"key":"units","label":"Unidades"}, {"key":"total","label":"Importe (Bs)"}]
        # Para ventas por sucursal/semana el total es el de la venta; para
        # artículos/categorías es la suma de subtotales de las partidas.
        return report_payload(report_key="sales", title=TITLES[kind], filters=filters,
            summary={"groups_count":len(rows),"sales_count":original["summary"]["sales_count"],"analysis_total":money(sum((a["total"] for _,a in sorted_items),Decimal("0"))),"analysis_kind":kind},
            columns=columns, rows=rows)

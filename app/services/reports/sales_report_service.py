from __future__ import annotations

from collections import Counter
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased, joinedload, selectinload

from app.models.category import Category
from app.models.payment import Payment
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User
from app.schemas.reports import SalesReportFilters
from app.services.reports.base import end_of_day, full_name, money, report_payload, start_of_day


class SalesReportService:
    COLUMNS = [
        {"key": "sale_code", "label": "Venta"},
        {"key": "date", "label": "Fecha"},
        {"key": "branch", "label": "Sucursal"},
        {"key": "customer", "label": "Cliente"},
        {"key": "cashier", "label": "Cajero"},
        {"key": "status", "label": "Estado"},
        {"key": "payment_methods", "label": "Método pago"},
        {"key": "products", "label": "Productos"},
        {"key": "items_quantity", "label": "Unidades"},
        {"key": "subtotal", "label": "Subtotal"},
        {"key": "discount", "label": "Descuento"},
        {"key": "total", "label": "Total"},
    ]

    @staticmethod
    def build(db: Session, filters: SalesReportFilters) -> dict:
        customer_search = aliased(User)

        stmt = (
            select(Sale)
            .options(
                joinedload(Sale.branch),
                joinedload(Sale.customer),
                joinedload(Sale.cashier),
                selectinload(Sale.payments),
                selectinload(Sale.items)
                .selectinload(SaleItem.product_variant)
                .joinedload(ProductVariant.product)
                .joinedload(Product.category),
            )
        )

        date_from = start_of_day(filters.date_from)
        date_to = end_of_day(filters.date_to)
        if date_from:
            stmt = stmt.where(Sale.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Sale.created_at <= date_to)
        if filters.branch_id:
            stmt = stmt.where(Sale.branch_id == filters.branch_id)
        if filters.customer_id:
            stmt = stmt.where(Sale.customer_id == filters.customer_id)
        if filters.cashier_id:
            stmt = stmt.where(Sale.cashier_id == filters.cashier_id)
        if filters.status:
            stmt = stmt.where(Sale.status == filters.status)
        if filters.min_total is not None:
            stmt = stmt.where(Sale.total_amount >= filters.min_total)
        if filters.max_total is not None:
            stmt = stmt.where(Sale.total_amount <= filters.max_total)

        if filters.product_id or filters.category_id or filters.audience_id:
            stmt = stmt.join(SaleItem, SaleItem.sale_id == Sale.id)
            stmt = stmt.join(ProductVariant, ProductVariant.id == SaleItem.product_variant_id)
            stmt = stmt.join(Product, Product.id == ProductVariant.product_id)
            if filters.product_id:
                stmt = stmt.where(Product.id == filters.product_id)
            if filters.category_id:
                stmt = stmt.where(Product.category_id == filters.category_id)
            if filters.audience_id:
                stmt = stmt.where(Product.audience_id == filters.audience_id)

        if filters.payment_method:
            stmt = stmt.join(Payment, Payment.sale_id == Sale.id)
            stmt = stmt.where(Payment.payment_method == filters.payment_method)

        if filters.search and filters.search.strip():
            term = f"%{filters.search.strip()}%"
            stmt = stmt.outerjoin(customer_search, customer_search.id == Sale.customer_id)
            stmt = stmt.where(
                or_(
                    Sale.sale_code.ilike(term),
                    customer_search.first_name.ilike(term),
                    customer_search.last_name.ilike(term),
                    customer_search.email.ilike(term),
                )
            )

        sales = db.scalars(stmt.distinct().order_by(Sale.created_at.desc())).unique().all()

        rows: list[dict] = []
        total_amount = Decimal("0")
        total_discount = Decimal("0")
        units = 0
        payment_counter: Counter[str] = Counter()

        for sale in sales:
            product_names: list[str] = []
            sale_units = 0
            for item in sale.items:
                sale_units += item.quantity
                variant = item.product_variant
                if variant and variant.product:
                    product_names.append(variant.product.name)

            methods = sorted({payment.payment_method for payment in sale.payments})
            payment_counter.update(methods)
            units += sale_units
            total_amount += Decimal(str(sale.total_amount))
            total_discount += Decimal(str(sale.discount_amount))

            rows.append(
                {
                    "sale_code": sale.sale_code,
                    "date": sale.created_at.isoformat(),
                    "branch": sale.branch.name if sale.branch else "—",
                    "customer": full_name(sale.customer) if sale.customer else "Consumidor final",
                    "cashier": full_name(sale.cashier),
                    "status": sale.status,
                    "payment_methods": ", ".join(methods) if methods else "—",
                    "products": ", ".join(dict.fromkeys(product_names)) or "—",
                    "items_quantity": sale_units,
                    "subtotal": money(sale.subtotal),
                    "discount": money(sale.discount_amount),
                    "total": money(sale.total_amount),
                }
            )

        count = len(sales)
        summary = {
            "sales_count": count,
            "units_sold": units,
            "gross_total": money(total_amount),
            "discount_total": money(total_discount),
            "average_ticket": money(total_amount / count) if count else 0.0,
            "payment_methods": dict(payment_counter),
        }

        return report_payload(
            report_key="sales",
            title="Reporte de ventas",
            filters=filters,
            summary=summary,
            columns=SalesReportService.COLUMNS,
            rows=rows,
        )

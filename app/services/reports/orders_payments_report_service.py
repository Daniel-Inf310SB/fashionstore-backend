from __future__ import annotations

from collections import Counter
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased, joinedload, selectinload

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.schemas.reports import OrdersPaymentsReportFilters
from app.services.reports.base import end_of_day, full_name, money, report_payload, start_of_day


class OrdersPaymentsReportService:
    COLUMNS = [
        {"key": "order_code", "label": "Compra"},
        {"key": "date", "label": "Fecha"},
        {"key": "branch", "label": "Sucursal"},
        {"key": "customer", "label": "Cliente"},
        {"key": "order_status", "label": "Estado compra"},
        {"key": "delivery_type", "label": "Entrega"},
        {"key": "products", "label": "Productos"},
        {"key": "items_quantity", "label": "Unidades"},
        {"key": "payment_methods", "label": "Método pago"},
        {"key": "payment_statuses", "label": "Estado pago"},
        {"key": "paid_amount", "label": "Monto aprobado"},
        {"key": "total", "label": "Total compra"},
    ]

    @staticmethod
    def build(db: Session, filters: OrdersPaymentsReportFilters) -> dict:
        customer_search = aliased(User)

        stmt = (
            select(Order)
            .options(
                joinedload(Order.branch),
                joinedload(Order.customer),
                selectinload(Order.payments),
                selectinload(Order.items)
                .selectinload(OrderItem.product_variant)
                .joinedload(ProductVariant.product)
                .joinedload(Product.category),
            )
        )

        date_from = start_of_day(filters.date_from)
        date_to = end_of_day(filters.date_to)
        if date_from:
            stmt = stmt.where(Order.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Order.created_at <= date_to)
        if filters.branch_id:
            stmt = stmt.where(Order.branch_id == filters.branch_id)
        if filters.customer_id:
            stmt = stmt.where(Order.customer_id == filters.customer_id)
        if filters.order_status:
            stmt = stmt.where(Order.status == filters.order_status)
        if filters.delivery_type:
            stmt = stmt.where(Order.delivery_type == filters.delivery_type)
        if filters.min_total is not None:
            stmt = stmt.where(Order.total_amount >= filters.min_total)
        if filters.max_total is not None:
            stmt = stmt.where(Order.total_amount <= filters.max_total)

        if filters.product_id or filters.category_id or filters.audience_id:
            stmt = stmt.join(OrderItem, OrderItem.order_id == Order.id)
            stmt = stmt.join(ProductVariant, ProductVariant.id == OrderItem.product_variant_id)
            stmt = stmt.join(Product, Product.id == ProductVariant.product_id)
            if filters.product_id:
                stmt = stmt.where(Product.id == filters.product_id)
            if filters.category_id:
                stmt = stmt.where(Product.category_id == filters.category_id)
            if filters.audience_id:
                stmt = stmt.where(Product.audience_id == filters.audience_id)

        if filters.payment_method or filters.payment_status:
            stmt = stmt.join(Payment, Payment.order_id == Order.id)
            if filters.payment_method:
                stmt = stmt.where(Payment.payment_method == filters.payment_method)
            if filters.payment_status:
                stmt = stmt.where(Payment.status == filters.payment_status)

        if filters.search and filters.search.strip():
            term = f"%{filters.search.strip()}%"
            stmt = stmt.join(customer_search, customer_search.id == Order.customer_id)
            stmt = stmt.where(
                or_(
                    Order.order_code.ilike(term),
                    customer_search.first_name.ilike(term),
                    customer_search.last_name.ilike(term),
                    customer_search.email.ilike(term),
                )
            )

        orders = db.scalars(stmt.distinct().order_by(Order.created_at.desc())).unique().all()

        rows: list[dict] = []
        total_orders = Decimal("0")
        approved_payments = Decimal("0")
        total_units = 0
        order_status_counter: Counter[str] = Counter()
        payment_status_counter: Counter[str] = Counter()

        for order in orders:
            names: list[str] = []
            units = 0
            for item in order.items:
                units += item.quantity
                if item.product_variant and item.product_variant.product:
                    names.append(item.product_variant.product.name)

            methods = sorted({payment.payment_method for payment in order.payments})
            statuses = sorted({payment.status for payment in order.payments})
            paid = sum(
                (Decimal(str(payment.amount)) for payment in order.payments if payment.status == "APPROVED"),
                Decimal("0"),
            )

            total_units += units
            total_orders += Decimal(str(order.total_amount))
            approved_payments += paid
            order_status_counter[order.status] += 1
            payment_status_counter.update(payment.status for payment in order.payments)

            rows.append(
                {
                    "order_code": order.order_code,
                    "date": order.created_at.isoformat(),
                    "branch": order.branch.name if order.branch else "—",
                    "customer": full_name(order.customer),
                    "order_status": order.status,
                    "delivery_type": order.delivery_type,
                    "products": ", ".join(dict.fromkeys(names)) or "—",
                    "items_quantity": units,
                    "payment_methods": ", ".join(methods) if methods else "—",
                    "payment_statuses": ", ".join(statuses) if statuses else "SIN PAGO",
                    "paid_amount": money(paid),
                    "total": money(order.total_amount),
                }
            )

        summary = {
            "orders_count": len(rows),
            "units": total_units,
            "orders_total": money(total_orders),
            "approved_payments_total": money(approved_payments),
            "by_order_status": dict(order_status_counter),
            "by_payment_status": dict(payment_status_counter),
        }

        return report_payload(
            report_key="orders-payments",
            title="Reporte de compras digitales y pagos",
            filters=filters,
            summary=summary,
            columns=OrdersPaymentsReportService.COLUMNS,
            rows=rows,
        )

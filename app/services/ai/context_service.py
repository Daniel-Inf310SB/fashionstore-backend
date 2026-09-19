from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Integer, case, func, or_
from sqlalchemy.orm import Session

from app.models.audience import Audience
from app.models.branch import Branch
from app.models.category import Category
from app.models.color import Color
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.reservation import Reservation
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.size import Size
from app.models.user import User
from app.services.branch_service import BranchService


class AIContextService:
    ADMIN_ROLES = {"ADMINISTRADOR", "SUPERADMIN"}
    BRANCH_ROLES = {"ENCARGADO_SUCURSAL"}
    EFFECTIVE_ORDER_STATUSES = ["PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED", "DELIVERED", "COMPLETED"]

    # Palabras demasiado comunes para aportar relevancia en búsqueda de catálogo.
    SEARCH_STOPWORDS = {
        "para", "con", "que", "quiero", "quisiera", "necesito", "busco", "algo",
        "una", "uno", "unos", "unas", "del", "las", "los", "por", "favor", "hasta",
        "menos", "mas", "muy", "tener", "tienen", "talla", "prenda", "prendas",
        "ropa", "recomienda", "recomiendame", "recomendacion", "muéstrame", "muestrame",
    }

    @staticmethod
    def _search_terms(text: str | None, *, max_terms: int = 8) -> list[str]:
        if not text:
            return []

        normalized = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", " ", text.lower())
        terms: list[str] = []
        for raw in normalized.split():
            token = raw.strip()
            if len(token) < 3 or token in AIContextService.SEARCH_STOPWORDS:
                continue
            if token not in terms:
                terms.append(token)
            if len(terms) >= max_terms:
                break
        return terms

    @staticmethod
    def _base_catalog_query(db: Session, *, branch_id: int):
        return (
            db.query(
                Product.id.label("product_id"),
                ProductVariant.id.label("variant_id"),
                Product.name.label("product_name"),
                Product.brand.label("brand"),
                Product.description.label("description"),
                Category.name.label("category"),
                Audience.name.label("audience"),
                Size.name.label("size"),
                Color.name.label("color"),
                (Product.base_price + ProductVariant.additional_price).label("price"),
                (Inventory.stock_quantity - Inventory.reserved_quantity).label("available"),
            )
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .join(Category, Category.id == Product.category_id)
            .join(Audience, Audience.id == Product.audience_id)
            .join(Size, Size.id == ProductVariant.size_id)
            .join(Color, Color.id == ProductVariant.color_id)
            .join(
                Inventory,
                (Inventory.product_variant_id == ProductVariant.id)
                & (Inventory.branch_id == branch_id),
            )
            .filter(
                Product.is_active.is_(True),
                ProductVariant.is_active.is_(True),
                Category.is_active.is_(True),
                Audience.is_active.is_(True),
                Size.is_active.is_(True),
                Color.is_active.is_(True),
                Inventory.is_active.is_(True),
                (Inventory.stock_quantity - Inventory.reserved_quantity) > 0,
            )
        )

    @staticmethod
    def _row_to_product(row) -> dict:
        return {
            "product_id": row.product_id,
            "variant_id": row.variant_id,
            "name": row.product_name,
            "brand": row.brand,
            "description": (row.description or "")[:220],
            "category": row.category,
            "audience": row.audience,
            "size": row.size,
            "color": row.color,
            "price": float(row.price),
            "available": int(row.available),
        }

    @staticmethod
    def _score_product(product: dict, *, terms: list[str], max_budget: Decimal | None) -> int:
        if not terms:
            # Sin texto útil, priorizamos disponibilidad y presupuesto.
            score = min(int(product["available"]), 20)
        else:
            searchable = {
                "name": str(product.get("name") or "").lower(),
                "brand": str(product.get("brand") or "").lower(),
                "description": str(product.get("description") or "").lower(),
                "category": str(product.get("category") or "").lower(),
                "audience": str(product.get("audience") or "").lower(),
                "size": str(product.get("size") or "").lower(),
                "color": str(product.get("color") or "").lower(),
            }
            weights = {
                "name": 8,
                "category": 7,
                "color": 7,
                "audience": 6,
                "brand": 5,
                "size": 5,
                "description": 3,
            }
            score = 0
            for term in terms:
                for field, value in searchable.items():
                    if term in value:
                        score += weights[field]
            score += min(int(product["available"]), 10)

        if max_budget is not None:
            price = Decimal(str(product["price"]))
            if price <= max_budget:
                score += 10
                # Dentro del presupuesto y cerca del límite suele ser una opción útil.
                if max_budget > 0 and price >= max_budget * Decimal("0.60"):
                    score += 3
        return score

    @staticmethod
    def catalog_context(
        db: Session,
        *,
        branch_id: int,
        query_text: str | None = None,
        size: str | None = None,
        category: str | None = None,
        max_budget: Decimal | None = None,
        limit: int = 15,
        candidate_pool: int = 60,
    ) -> list[dict]:
        """
        Recupera un conjunto pequeño y relevante del catálogo.

        Los filtros explícitos (talla/categoría/presupuesto) son duros. El texto libre se
        usa para recuperar coincidencias y posteriormente aplicar scoring local, de modo
        que OpenAI no necesite recibir el catálogo completo.
        """
        query = AIContextService._base_catalog_query(db, branch_id=branch_id)

        if size and size.strip():
            query = query.filter(Size.name.ilike(size.strip()))

        if category and category.strip():
            query = query.filter(Category.name.ilike(category.strip()))

        if max_budget is not None:
            query = query.filter(
                (Product.base_price + ProductVariant.additional_price) <= max_budget
            )

        terms = AIContextService._search_terms(query_text)
        if terms:
            term_filters = []
            for term in terms:
                pattern = f"%{term}%"
                term_filters.extend(
                    [
                        Product.name.ilike(pattern),
                        Product.brand.ilike(pattern),
                        Product.description.ilike(pattern),
                        Category.name.ilike(pattern),
                        Audience.name.ilike(pattern),
                        Size.name.ilike(pattern),
                        Color.name.ilike(pattern),
                    ]
                )
            query = query.filter(or_(*term_filters))

        pool_limit = max(limit, min(max(candidate_pool, limit), 100))
        rows = (
            query.order_by(
                (Inventory.stock_quantity - Inventory.reserved_quantity).desc(),
                Product.id.asc(),
            )
            .limit(pool_limit)
            .all()
        )

        products = [AIContextService._row_to_product(row) for row in rows]

        # Si una consulta textual fue demasiado restrictiva, hacemos fallback a los filtros
        # duros para que el asistente todavía pueda sugerir alternativas disponibles.
        if not products and terms:
            fallback = AIContextService._base_catalog_query(db, branch_id=branch_id)
            if size and size.strip():
                fallback = fallback.filter(Size.name.ilike(size.strip()))
            if category and category.strip():
                fallback = fallback.filter(Category.name.ilike(category.strip()))
            if max_budget is not None:
                fallback = fallback.filter(
                    (Product.base_price + ProductVariant.additional_price) <= max_budget
                )
            rows = (
                fallback.order_by(
                    (Inventory.stock_quantity - Inventory.reserved_quantity).desc(),
                    Product.id.asc(),
                )
                .limit(pool_limit)
                .all()
            )
            products = [AIContextService._row_to_product(row) for row in rows]

        scored = [
            (AIContextService._score_product(p, terms=terms, max_budget=max_budget), p)
            for p in products
        ]
        scored.sort(key=lambda item: (item[0], item[1]["available"]), reverse=True)
        return [p for _, p in scored[: max(1, min(limit, 30))]]

    @staticmethod
    def assistant_catalog_context(
        db: Session,
        *,
        branch_id: int,
        message: str,
        limit: int = 15,
    ) -> list[dict]:
        return AIContextService.catalog_context(
            db,
            branch_id=branch_id,
            query_text=message,
            limit=limit,
            candidate_pool=max(limit * 4, 40),
        )

    @staticmethod
    def resolve_report_branch(
        db: Session,
        *,
        current_user: User,
        requested_branch_id: int | None,
    ) -> int | None:
        role = current_user.role.name.strip().upper() if current_user.role else ""

        if role in AIContextService.ADMIN_ROLES:
            if requested_branch_id is not None and db.get(Branch, requested_branch_id) is None:
                raise LookupError("Sucursal no encontrada.")
            return requested_branch_id

        if role in AIContextService.BRANCH_ROLES:
            branch = BranchService.get_my_branch(db=db, user_id=current_user.id)
            if requested_branch_id is not None and requested_branch_id != branch.id:
                raise PermissionError("No puedes generar reportes de otra sucursal.")
            return branch.id

        raise PermissionError("Tu rol no puede generar reportes inteligentes.")

    @staticmethod
    def _period_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        return start_dt, end_dt

    @staticmethod
    def _commercial_summary(
        db: Session,
        *,
        branch_id: int | None,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict:
        sale_query = db.query(
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.total_amount), 0),
            func.coalesce(func.avg(Sale.total_amount), 0),
        ).filter(
            Sale.status == "PAID",
            Sale.created_at >= start_dt,
            Sale.created_at < end_dt,
        )
        order_query = db.query(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
            func.coalesce(func.avg(Order.total_amount), 0),
        ).filter(
            Order.status.in_(AIContextService.EFFECTIVE_ORDER_STATUSES),
            Order.created_at >= start_dt,
            Order.created_at < end_dt,
        )

        if branch_id is not None:
            sale_query = sale_query.filter(Sale.branch_id == branch_id)
            order_query = order_query.filter(Order.branch_id == branch_id)

        sales = sale_query.one()
        orders = order_query.one()
        total_revenue = Decimal(str(sales[1] or 0)) + Decimal(str(orders[1] or 0))
        total_transactions = int(sales[0] or 0) + int(orders[0] or 0)

        return {
            "sales": {
                "paid_count": int(sales[0] or 0),
                "revenue": float(sales[1] or 0),
                "average_ticket": float(sales[2] or 0),
            },
            "digital_orders": {
                "effective_count": int(orders[0] or 0),
                "revenue": float(orders[1] or 0),
                "average_ticket": float(orders[2] or 0),
            },
            "commerce_total": {
                "transactions": total_transactions,
                "revenue": float(total_revenue),
                "average_ticket": float(total_revenue / total_transactions) if total_transactions else 0.0,
            },
        }

    @staticmethod
    def _product_sales_metrics(
        db: Session,
        *,
        branch_id: int | None,
        start_dt: datetime,
        end_dt: datetime,
        limit: int,
    ) -> tuple[list[dict], list[dict]]:
        """Combina venta presencial + compra digital por producto y categoría."""
        aggregate: dict[int, dict] = {}
        category_aggregate: dict[str, dict] = defaultdict(lambda: {"units_sold": 0, "revenue": Decimal("0")})

        sale_rows = (
            db.query(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Category.name.label("category_name"),
                func.sum(SaleItem.quantity).label("units"),
                func.sum(SaleItem.subtotal).label("revenue"),
            )
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(ProductVariant, ProductVariant.id == SaleItem.product_variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Category, Category.id == Product.category_id)
            .filter(
                Sale.status == "PAID",
                Sale.created_at >= start_dt,
                Sale.created_at < end_dt,
            )
        )
        if branch_id is not None:
            sale_rows = sale_rows.filter(Sale.branch_id == branch_id)
        sale_rows = sale_rows.group_by(Product.id, Product.name, Category.name).all()

        order_rows = (
            db.query(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Category.name.label("category_name"),
                func.sum(OrderItem.quantity).label("units"),
                func.sum(OrderItem.subtotal).label("revenue"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .join(ProductVariant, ProductVariant.id == OrderItem.product_variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Category, Category.id == Product.category_id)
            .filter(
                Order.status.in_(AIContextService.EFFECTIVE_ORDER_STATUSES),
                Order.created_at >= start_dt,
                Order.created_at < end_dt,
            )
        )
        if branch_id is not None:
            order_rows = order_rows.filter(Order.branch_id == branch_id)
        order_rows = order_rows.group_by(Product.id, Product.name, Category.name).all()

        for row in [*sale_rows, *order_rows]:
            entry = aggregate.setdefault(
                int(row.product_id),
                {
                    "product_id": int(row.product_id),
                    "name": row.product_name,
                    "category": row.category_name,
                    "units_sold": 0,
                    "revenue": Decimal("0"),
                },
            )
            units = int(row.units or 0)
            revenue = Decimal(str(row.revenue or 0))
            entry["units_sold"] += units
            entry["revenue"] += revenue
            category_aggregate[row.category_name]["units_sold"] += units
            category_aggregate[row.category_name]["revenue"] += revenue

        top_products = sorted(
            aggregate.values(),
            key=lambda item: (item["units_sold"], item["revenue"]),
            reverse=True,
        )[:limit]
        normalized_products = [
            {
                **item,
                "revenue": float(item["revenue"]),
            }
            for item in top_products
        ]

        categories = sorted(
            (
                {
                    "category": category,
                    "units_sold": values["units_sold"],
                    "revenue": float(values["revenue"]),
                }
                for category, values in category_aggregate.items()
            ),
            key=lambda item: (item["revenue"], item["units_sold"]),
            reverse=True,
        )[:limit]

        return normalized_products, categories

    @staticmethod
    def _inventory_details(
        db: Session,
        *,
        branch_id: int | None,
        sold_variant_ids: set[int],
        limit: int,
    ) -> tuple[dict, list[dict], list[dict]]:
        available_expr = Inventory.stock_quantity - Inventory.reserved_quantity
        low_case = case((available_expr <= Inventory.reorder_point, 1), else_=0)

        summary_query = db.query(
            func.count(Inventory.id),
            func.coalesce(func.sum(available_expr), 0),
            func.coalesce(func.sum(low_case), 0),
        ).filter(Inventory.is_active.is_(True))
        if branch_id is not None:
            summary_query = summary_query.filter(Inventory.branch_id == branch_id)
        summary = summary_query.one()

        details_query = (
            db.query(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                ProductVariant.id.label("variant_id"),
                Size.name.label("size"),
                Color.name.label("color"),
                available_expr.label("available"),
                Inventory.reorder_point.label("reorder_point"),
            )
            .join(ProductVariant, ProductVariant.id == Inventory.product_variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Size, Size.id == ProductVariant.size_id)
            .join(Color, Color.id == ProductVariant.color_id)
            .filter(Inventory.is_active.is_(True), Product.is_active.is_(True), ProductVariant.is_active.is_(True))
        )
        if branch_id is not None:
            details_query = details_query.filter(Inventory.branch_id == branch_id)

        low_stock_rows = (
            details_query.filter(available_expr <= Inventory.reorder_point)
            .order_by(available_expr.asc(), Product.name.asc())
            .limit(limit)
            .all()
        )
        low_stock = [
            {
                "product_id": int(row.product_id),
                "variant_id": int(row.variant_id),
                "name": row.product_name,
                "size": row.size,
                "color": row.color,
                "available": int(row.available or 0),
                "reorder_point": int(row.reorder_point or 0),
            }
            for row in low_stock_rows
        ]

        zero_rotation_query = details_query.filter(available_expr > 0)
        if sold_variant_ids:
            zero_rotation_query = zero_rotation_query.filter(~ProductVariant.id.in_(sold_variant_ids))
        zero_rotation_rows = (
            zero_rotation_query.order_by(available_expr.desc(), Product.name.asc())
            .limit(limit)
            .all()
        )
        zero_rotation = [
            {
                "product_id": int(row.product_id),
                "variant_id": int(row.variant_id),
                "name": row.product_name,
                "size": row.size,
                "color": row.color,
                "available": int(row.available or 0),
                "definition": "Con stock disponible y sin unidades vendidas en el periodo seleccionado.",
            }
            for row in zero_rotation_rows
        ]

        return (
            {
                "variant_rows": int(summary[0] or 0),
                "available_units": int(summary[1] or 0),
                "low_stock_rows": int(summary[2] or 0),
            },
            low_stock,
            zero_rotation,
        )

    @staticmethod
    def _reservation_metrics(
        db: Session,
        *,
        branch_id: int | None,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict:
        base = db.query(Reservation).filter(
            Reservation.created_at >= start_dt,
            Reservation.created_at < end_dt,
        )
        if branch_id is not None:
            base = base.filter(Reservation.branch_id == branch_id)

        total = base.count()
        completed = base.filter(Reservation.status == "COMPLETED").count()
        expired = base.filter(Reservation.status == "EXPIRED").count()
        cancelled = base.filter(Reservation.status == "CANCELLED").count()

        return {
            "total": int(total),
            "completed": int(completed),
            "expired": int(expired),
            "cancelled": int(cancelled),
            "completion_rate": round((completed / total) * 100, 2) if total else 0.0,
            "expiration_rate": round((expired / total) * 100, 2) if total else 0.0,
        }

    @staticmethod
    def report_context(
        db: Session,
        *,
        branch_id: int | None,
        start_date: date | None,
        end_date: date | None,
        detail_limit: int = 5,
    ) -> tuple[dict, date, date]:
        today = datetime.now(timezone.utc).date()
        resolved_end = end_date or today
        resolved_start = start_date or (resolved_end - timedelta(days=29))

        start_dt, end_dt = AIContextService._period_bounds(resolved_start, resolved_end)
        current_summary = AIContextService._commercial_summary(
            db,
            branch_id=branch_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        period_days = (resolved_end - resolved_start).days + 1
        previous_end = resolved_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=period_days - 1)
        previous_start_dt, previous_end_dt = AIContextService._period_bounds(previous_start, previous_end)
        previous_summary = AIContextService._commercial_summary(
            db,
            branch_id=branch_id,
            start_dt=previous_start_dt,
            end_dt=previous_end_dt,
        )

        current_revenue = current_summary["commerce_total"]["revenue"]
        previous_revenue = previous_summary["commerce_total"]["revenue"]
        if previous_revenue:
            revenue_change_pct = round(((current_revenue - previous_revenue) / previous_revenue) * 100, 2)
        else:
            revenue_change_pct = None

        top_products, sales_by_category = AIContextService._product_sales_metrics(
            db,
            branch_id=branch_id,
            start_dt=start_dt,
            end_dt=end_dt,
            limit=detail_limit,
        )
        sold_variant_ids: set[int] = set()

        # Para detectar cero rotación necesitamos todas las variantes vendidas, no solo los productos del top.
        sold_sale_ids = db.query(ProductVariant.id).join(Product, Product.id == ProductVariant.product_id).join(
            SaleItem, SaleItem.product_variant_id == ProductVariant.id
        ).join(Sale, Sale.id == SaleItem.sale_id).filter(
            Sale.status == "PAID", Sale.created_at >= start_dt, Sale.created_at < end_dt
        )
        sold_order_ids = db.query(ProductVariant.id).join(Product, Product.id == ProductVariant.product_id).join(
            OrderItem, OrderItem.product_variant_id == ProductVariant.id
        ).join(Order, Order.id == OrderItem.order_id).filter(
            Order.status.in_(AIContextService.EFFECTIVE_ORDER_STATUSES),
            Order.created_at >= start_dt,
            Order.created_at < end_dt,
        )
        if branch_id is not None:
            sold_sale_ids = sold_sale_ids.filter(Sale.branch_id == branch_id)
            sold_order_ids = sold_order_ids.filter(Order.branch_id == branch_id)
        sold_variant_ids.update(int(row[0]) for row in sold_sale_ids.distinct().all())
        sold_variant_ids.update(int(row[0]) for row in sold_order_ids.distinct().all())

        inventory_summary, low_stock, zero_rotation = AIContextService._inventory_details(
            db,
            branch_id=branch_id,
            sold_variant_ids=sold_variant_ids,
            limit=detail_limit,
        )
        reservations = AIContextService._reservation_metrics(
            db,
            branch_id=branch_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        branch_name = None
        if branch_id is not None:
            branch = db.get(Branch, branch_id)
            branch_name = branch.name if branch else None

        data = {
            "branch": {"id": branch_id, "name": branch_name} if branch_id is not None else {"scope": "all"},
            "sales": current_summary["sales"],
            "digital_orders": current_summary["digital_orders"],
            "commerce_total": current_summary["commerce_total"],
            "comparison": {
                "previous_period": {
                    "start": previous_start.isoformat(),
                    "end": previous_end.isoformat(),
                    "commerce_total": previous_summary["commerce_total"],
                },
                "revenue_change_pct": revenue_change_pct,
                "note": (
                    "revenue_change_pct es null cuando el periodo anterior tuvo ingresos 0; "
                    "no debe interpretarse como 0% de cambio."
                ),
            },
            "reservations": reservations,
            "inventory": inventory_summary,
            "top_products": top_products,
            "sales_by_category": sales_by_category,
            "low_stock_products": low_stock,
            "zero_rotation_products": zero_rotation,
            "definitions": {
                "zero_rotation_products": "Variantes con stock disponible y sin ventas presenciales ni digitales efectivas en el periodo.",
                "low_stock_products": "Variantes cuya disponibilidad es menor o igual a su punto de reposición.",
            },
        }

        return data, resolved_start, resolved_end

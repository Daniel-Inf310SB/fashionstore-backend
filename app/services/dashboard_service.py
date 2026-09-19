from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.employee_branch import EmployeeBranch
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.reservation import Reservation
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User


MONEY = Decimal("0.01")
PERCENT = Decimal("0.01")


class DashboardService:
    POS_REVENUE_STATUSES = {"PAID"}
    DIGITAL_REVENUE_STATUSES = {
        "PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED", "DELIVERED", "COMPLETED"
    }
    RESERVATION_ATTENTION_STATUSES = {"PENDING", "CONFIRMED", "PREPARING", "READY"}

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value or 0).quantize(MONEY, rounding=ROUND_HALF_UP)

    @staticmethod
    def _percent_change(current: Decimal | int, previous: Decimal | int) -> Decimal | None:
        current_d = Decimal(current or 0)
        previous_d = Decimal(previous or 0)
        if previous_d == 0:
            return Decimal("0.00") if current_d == 0 else None
        return (((current_d - previous_d) / previous_d) * Decimal("100")).quantize(
            PERCENT, rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _date_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        return start, end

    @staticmethod
    def _role_name(user: User) -> str:
        return str(getattr(getattr(user, "role", None), "name", "") or "").upper()

    @staticmethod
    def _resolve_scope(db: Session, user: User, requested_branch_id: int | None):
        role = DashboardService._role_name(user)

        active_branches = (
            db.query(Branch)
            .filter(Branch.is_active.is_(True))
            .order_by(Branch.name.asc())
            .all()
        )

        if role == "ADMINISTRADOR":
            if requested_branch_id is not None:
                selected = next((b for b in active_branches if b.id == requested_branch_id), None)
                if selected is None:
                    raise LookupError("La sucursal solicitada no existe o está inactiva.")
                branch_ids = [selected.id]
                mode = "BRANCH"
                branch_name = selected.name
            else:
                branch_ids = [b.id for b in active_branches]
                mode = "ALL_BRANCHES"
                branch_name = None

            options = [{"id": b.id, "name": b.name} for b in active_branches]
            return branch_ids, mode, requested_branch_id, branch_name, options

        if role == "ENCARGADO_SUCURSAL":
            assignment = (
                db.query(EmployeeBranch)
                .join(Branch, Branch.id == EmployeeBranch.branch_id)
                .filter(
                    EmployeeBranch.user_id == user.id,
                    EmployeeBranch.is_active.is_(True),
                    Branch.is_active.is_(True),
                )
                .first()
            )
            if assignment is None:
                raise PermissionError("No tienes una sucursal activa asignada.")
            if requested_branch_id is not None and requested_branch_id != assignment.branch_id:
                raise PermissionError("Solo puedes consultar el dashboard de tu sucursal asignada.")

            branch = assignment.branch
            return (
                [branch.id],
                "BRANCH",
                branch.id,
                branch.name,
                [{"id": branch.id, "name": branch.name}],
            )

        raise PermissionError("Tu rol no puede consultar el dashboard administrativo.")

    @staticmethod
    def _aggregate_revenue(db: Session, branch_ids: list[int], start: datetime, end: datetime):
        if not branch_ids:
            return Decimal("0.00"), 0, 0, 0

        pos = (
            db.query(
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.count(Sale.id),
            )
            .filter(
                Sale.branch_id.in_(branch_ids),
                Sale.status.in_(DashboardService.POS_REVENUE_STATUSES),
                Sale.created_at >= start,
                Sale.created_at < end,
            )
            .one()
        )
        digital = (
            db.query(
                func.coalesce(func.sum(Order.total_amount), 0),
                func.count(Order.id),
            )
            .filter(
                Order.branch_id.in_(branch_ids),
                Order.status.in_(DashboardService.DIGITAL_REVENUE_STATUSES),
                Order.created_at >= start,
                Order.created_at < end,
            )
            .one()
        )
        pos_revenue = DashboardService._money(pos[0])
        digital_revenue = DashboardService._money(digital[0])
        pos_count = int(pos[1] or 0)
        digital_count = int(digital[1] or 0)
        return (
            pos_revenue + digital_revenue,
            pos_count + digital_count,
            pos_count,
            digital_count,
            pos_revenue,
            digital_revenue,
        )

    @staticmethod
    def _sales_trend(db: Session, branch_ids: list[int], date_from: date, date_to: date):
        start, end = DashboardService._date_bounds(date_from, date_to)
        buckets: dict[date, dict[str, Decimal | int]] = {}
        cursor = date_from
        while cursor <= date_to:
            buckets[cursor] = {
                "pos_revenue": Decimal("0.00"),
                "digital_revenue": Decimal("0.00"),
                "pos_count": 0,
                "digital_count": 0,
            }
            cursor += timedelta(days=1)

        if branch_ids:
            pos_rows = (
                db.query(
                    func.date(Sale.created_at),
                    func.coalesce(func.sum(Sale.total_amount), 0),
                    func.count(Sale.id),
                )
                .filter(
                    Sale.branch_id.in_(branch_ids),
                    Sale.status.in_(DashboardService.POS_REVENUE_STATUSES),
                    Sale.created_at >= start,
                    Sale.created_at < end,
                )
                .group_by(func.date(Sale.created_at))
                .all()
            )
            for day, revenue, count in pos_rows:
                if day in buckets:
                    buckets[day]["pos_revenue"] = DashboardService._money(revenue)
                    buckets[day]["pos_count"] = int(count or 0)

            digital_rows = (
                db.query(
                    func.date(Order.created_at),
                    func.coalesce(func.sum(Order.total_amount), 0),
                    func.count(Order.id),
                )
                .filter(
                    Order.branch_id.in_(branch_ids),
                    Order.status.in_(DashboardService.DIGITAL_REVENUE_STATUSES),
                    Order.created_at >= start,
                    Order.created_at < end,
                )
                .group_by(func.date(Order.created_at))
                .all()
            )
            for day, revenue, count in digital_rows:
                if day in buckets:
                    buckets[day]["digital_revenue"] = DashboardService._money(revenue)
                    buckets[day]["digital_count"] = int(count or 0)

        result = []
        for day in sorted(buckets):
            row = buckets[day]
            pos_revenue = DashboardService._money(row["pos_revenue"])
            digital_revenue = DashboardService._money(row["digital_revenue"])
            result.append({
                "date": day,
                "pos_revenue": pos_revenue,
                "digital_revenue": digital_revenue,
                "total_revenue": DashboardService._money(pos_revenue + digital_revenue),
                "transactions": int(row["pos_count"]) + int(row["digital_count"]),
            })
        return result

    @staticmethod
    def _top_products(db: Session, branch_ids: list[int], start: datetime, end: datetime, limit: int = 8):
        aggregated: dict[int, dict] = {}

        if branch_ids:
            pos_rows = (
                db.query(
                    Product.id,
                    Product.name,
                    func.coalesce(func.sum(SaleItem.quantity), 0),
                    func.coalesce(func.sum(SaleItem.subtotal), 0),
                )
                .join(ProductVariant, ProductVariant.id == SaleItem.product_variant_id)
                .join(Product, Product.id == ProductVariant.product_id)
                .join(Sale, Sale.id == SaleItem.sale_id)
                .filter(
                    Sale.branch_id.in_(branch_ids),
                    Sale.status.in_(DashboardService.POS_REVENUE_STATUSES),
                    Sale.created_at >= start,
                    Sale.created_at < end,
                )
                .group_by(Product.id, Product.name)
                .all()
            )
            for product_id, name, units, revenue in pos_rows:
                aggregated[product_id] = {
                    "product_id": product_id,
                    "product_name": name,
                    "units": int(units or 0),
                    "revenue": DashboardService._money(revenue),
                }

            digital_rows = (
                db.query(
                    Product.id,
                    Product.name,
                    func.coalesce(func.sum(OrderItem.quantity), 0),
                    func.coalesce(func.sum(OrderItem.subtotal), 0),
                )
                .join(ProductVariant, ProductVariant.id == OrderItem.product_variant_id)
                .join(Product, Product.id == ProductVariant.product_id)
                .join(Order, Order.id == OrderItem.order_id)
                .filter(
                    Order.branch_id.in_(branch_ids),
                    Order.status.in_(DashboardService.DIGITAL_REVENUE_STATUSES),
                    Order.created_at >= start,
                    Order.created_at < end,
                )
                .group_by(Product.id, Product.name)
                .all()
            )
            for product_id, name, units, revenue in digital_rows:
                row = aggregated.setdefault(product_id, {
                    "product_id": product_id,
                    "product_name": name,
                    "units": 0,
                    "revenue": Decimal("0.00"),
                })
                row["units"] += int(units or 0)
                row["revenue"] = DashboardService._money(row["revenue"] + DashboardService._money(revenue))

        return sorted(
            aggregated.values(),
            key=lambda item: (item["units"], item["revenue"]),
            reverse=True,
        )[:limit]

    @staticmethod
    def _reservation_statuses(db: Session, branch_ids: list[int], start: datetime, end: datetime):
        statuses = [
            "PENDING", "CONFIRMED", "PREPARING", "READY", "ATTENDED",
            "COMPLETED", "CANCELLED", "EXPIRED",
        ]
        counts = {status: 0 for status in statuses}
        if branch_ids:
            rows = (
                db.query(Reservation.status, func.count(Reservation.id))
                .filter(
                    Reservation.branch_id.in_(branch_ids),
                    Reservation.created_at >= start,
                    Reservation.created_at < end,
                )
                .group_by(Reservation.status)
                .all()
            )
            for status, count in rows:
                counts[str(status)] = int(count or 0)
        return [{"status": status, "count": counts.get(status, 0)} for status in statuses]

    @staticmethod
    def _inventory_metrics(db: Session, branch_ids: list[int], low_stock_limit: int = 10):
        if not branch_ids:
            return 0, 0, []

        rows = (
            db.query(Inventory, Branch, ProductVariant, Product)
            .join(Branch, Branch.id == Inventory.branch_id)
            .join(ProductVariant, ProductVariant.id == Inventory.product_variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .filter(
                Inventory.branch_id.in_(branch_ids),
                Inventory.is_active.is_(True),
                ProductVariant.is_active.is_(True),
                Product.is_active.is_(True),
            )
            .all()
        )

        low_count = 0
        out_count = 0
        critical = []
        for inventory, branch, variant, product in rows:
            available = int(inventory.stock_quantity or 0) - int(inventory.reserved_quantity or 0)
            if available <= 0:
                state = "OUT_OF_STOCK"
                out_count += 1
            elif available <= int(inventory.reorder_point or 0):
                state = "LOW_STOCK"
                low_count += 1
            else:
                continue

            critical.append({
                "inventory_id": inventory.id,
                "branch_id": branch.id,
                "branch_name": branch.name,
                "product_id": product.id,
                "product_name": product.name,
                "sku": variant.sku,
                "available_quantity": available,
                "reorder_point": int(inventory.reorder_point or 0),
                "stock_state": state,
            })

        critical.sort(
            key=lambda item: (
                0 if item["stock_state"] == "OUT_OF_STOCK" else 1,
                item["available_quantity"],
                item["product_name"].lower(),
            )
        )
        return low_count, out_count, critical[:low_stock_limit]

    @staticmethod
    def _branch_performance(db: Session, branch_ids: list[int], start: datetime, end: datetime):
        if not branch_ids:
            return []

        branches = (
            db.query(Branch)
            .filter(Branch.id.in_(branch_ids))
            .order_by(Branch.name.asc())
            .all()
        )
        result = []
        for branch in branches:
            revenue, tx_count, _, _, _, _ = DashboardService._aggregate_revenue(
                db, [branch.id], start, end
            )
            reservations_attention = (
                db.query(func.count(Reservation.id))
                .filter(
                    Reservation.branch_id == branch.id,
                    Reservation.status.in_(DashboardService.RESERVATION_ATTENTION_STATUSES),
                )
                .scalar()
                or 0
            )
            inv_rows = (
                db.query(Inventory.stock_quantity, Inventory.reserved_quantity, Inventory.reorder_point)
                .filter(
                    Inventory.branch_id == branch.id,
                    Inventory.is_active.is_(True),
                )
                .all()
            )
            low_stock = sum(
                1
                for stock, reserved, reorder in inv_rows
                if (int(stock or 0) - int(reserved or 0)) <= int(reorder or 0)
            )
            result.append({
                "branch_id": branch.id,
                "branch_name": branch.name,
                "revenue": revenue,
                "transactions": tx_count,
                "reservations_attention": int(reservations_attention),
                "low_stock_variants": low_stock,
            })
        return sorted(result, key=lambda item: item["revenue"], reverse=True)

    @staticmethod
    def _recent_activity(db: Session, branch_ids: list[int], limit: int = 12):
        if not branch_ids:
            return []

        branch_names = {
            b.id: b.name
            for b in db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
        }
        items = []

        for row in (
            db.query(Sale)
            .filter(Sale.branch_id.in_(branch_ids))
            .order_by(Sale.created_at.desc())
            .limit(limit)
            .all()
        ):
            items.append({
                "type": "SALE",
                "id": row.id,
                "code": row.sale_code,
                "branch_id": row.branch_id,
                "branch_name": branch_names.get(row.branch_id, "Sucursal"),
                "status": row.status,
                "amount": DashboardService._money(row.total_amount),
                "created_at": row.created_at,
            })

        for row in (
            db.query(Order)
            .filter(Order.branch_id.in_(branch_ids))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .all()
        ):
            items.append({
                "type": "ORDER",
                "id": row.id,
                "code": row.order_code,
                "branch_id": row.branch_id,
                "branch_name": branch_names.get(row.branch_id, "Sucursal"),
                "status": row.status,
                "amount": DashboardService._money(row.total_amount),
                "created_at": row.created_at,
            })

        for row in (
            db.query(Reservation)
            .filter(Reservation.branch_id.in_(branch_ids))
            .order_by(Reservation.created_at.desc())
            .limit(limit)
            .all()
        ):
            items.append({
                "type": "RESERVATION",
                "id": row.id,
                "code": row.reservation_code,
                "branch_id": row.branch_id,
                "branch_name": branch_names.get(row.branch_id, "Sucursal"),
                "status": row.status,
                "amount": None,
                "created_at": row.created_at,
            })

        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items[:limit]

    @staticmethod
    def build(
        db: Session,
        *,
        current_user: User,
        branch_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        today = datetime.now(timezone.utc).date()
        date_to = date_to or today
        date_from = date_from or (date_to - timedelta(days=29))

        if date_from > date_to:
            raise ValueError("date_from no puede ser posterior a date_to.")
        if (date_to - date_from).days > 366:
            raise ValueError("El dashboard admite un rango máximo de 367 días.")

        branch_ids, mode, effective_branch_id, branch_name, options = DashboardService._resolve_scope(
            db, current_user, branch_id
        )

        start, end = DashboardService._date_bounds(date_from, date_to)
        period_days = (date_to - date_from).days + 1
        previous_to = date_from - timedelta(days=1)
        previous_from = previous_to - timedelta(days=period_days - 1)
        previous_start, previous_end = DashboardService._date_bounds(previous_from, previous_to)

        revenue, transactions, pos_count, digital_count, pos_revenue, digital_revenue = DashboardService._aggregate_revenue(
            db, branch_ids, start, end
        )
        prev_revenue, prev_transactions, _, _, _, _ = DashboardService._aggregate_revenue(
            db, branch_ids, previous_start, previous_end
        )

        reservation_attention = 0
        reservation_ready = 0
        if branch_ids:
            reservation_attention = int(
                db.query(func.count(Reservation.id))
                .filter(
                    Reservation.branch_id.in_(branch_ids),
                    Reservation.status.in_(DashboardService.RESERVATION_ATTENTION_STATUSES),
                )
                .scalar()
                or 0
            )
            reservation_ready = int(
                db.query(func.count(Reservation.id))
                .filter(
                    Reservation.branch_id.in_(branch_ids),
                    Reservation.status == "READY",
                )
                .scalar()
                or 0
            )

        low_stock_count, out_of_stock_count, low_stock_items = DashboardService._inventory_metrics(
            db, branch_ids
        )

        average_ticket = DashboardService._money(
            revenue / transactions if transactions else Decimal("0.00")
        )

        return {
            "generated_at": datetime.now(timezone.utc),
            "scope": {
                "mode": mode,
                "branch_id": effective_branch_id,
                "branch_name": branch_name,
                "available_branches": options,
            },
            "period": {
                "date_from": date_from,
                "date_to": date_to,
                "previous_from": previous_from,
                "previous_to": previous_to,
            },
            "kpis": {
                "revenue": DashboardService._money(revenue),
                "pos_revenue": DashboardService._money(pos_revenue),
                "digital_revenue": DashboardService._money(digital_revenue),
                "revenue_change_pct": DashboardService._percent_change(revenue, prev_revenue),
                "transactions_count": transactions,
                "transactions_change_pct": DashboardService._percent_change(transactions, prev_transactions),
                "average_ticket": average_ticket,
                "pos_sales_count": pos_count,
                "digital_orders_count": digital_count,
                "reservations_attention": reservation_attention,
                "reservations_ready": reservation_ready,
                "low_stock_variants": low_stock_count,
                "out_of_stock_variants": out_of_stock_count,
            },
            "sales_trend": DashboardService._sales_trend(db, branch_ids, date_from, date_to),
            "top_products": DashboardService._top_products(db, branch_ids, start, end),
            "reservation_statuses": DashboardService._reservation_statuses(db, branch_ids, start, end),
            "low_stock": low_stock_items,
            "branch_performance": DashboardService._branch_performance(db, branch_ids, start, end),
            "recent_activity": DashboardService._recent_activity(db, branch_ids),
        }

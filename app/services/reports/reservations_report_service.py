from __future__ import annotations

from collections import Counter
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased, joinedload, selectinload

from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.reservation import Reservation
from app.models.reservation_item import ReservationItem
from app.models.user import User
from app.schemas.reports import ReservationsReportFilters
from app.services.reports.base import end_of_day, full_name, money, report_payload, start_of_day


class ReservationsReportService:
    COLUMNS = [
        {"key": "reservation_code", "label": "Reserva"},
        {"key": "date", "label": "Fecha"},
        {"key": "branch", "label": "Sucursal"},
        {"key": "customer", "label": "Cliente"},
        {"key": "status", "label": "Estado"},
        {"key": "expires_at", "label": "Vence"},
        {"key": "products", "label": "Productos"},
        {"key": "items_quantity", "label": "Unidades"},
        {"key": "estimated_total", "label": "Total estimado"},
        {"key": "item_statuses", "label": "Estado ítems"},
    ]

    @staticmethod
    def build(db: Session, filters: ReservationsReportFilters) -> dict:
        customer_search = aliased(User)

        stmt = (
            select(Reservation)
            .options(
                joinedload(Reservation.branch),
                joinedload(Reservation.customer),
                selectinload(Reservation.items)
                .selectinload(ReservationItem.product_variant)
                .joinedload(ProductVariant.product)
                .joinedload(Product.category),
            )
        )

        date_from = start_of_day(filters.date_from)
        date_to = end_of_day(filters.date_to)
        if date_from:
            stmt = stmt.where(Reservation.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Reservation.created_at <= date_to)
        if filters.branch_id:
            stmt = stmt.where(Reservation.branch_id == filters.branch_id)
        if filters.customer_id:
            stmt = stmt.where(Reservation.customer_id == filters.customer_id)
        if filters.status:
            stmt = stmt.where(Reservation.status == filters.status)

        if filters.product_id or filters.category_id or filters.audience_id or filters.item_status:
            stmt = stmt.join(ReservationItem, ReservationItem.reservation_id == Reservation.id)
            stmt = stmt.join(ProductVariant, ProductVariant.id == ReservationItem.product_variant_id)
            stmt = stmt.join(Product, Product.id == ProductVariant.product_id)
            if filters.product_id:
                stmt = stmt.where(Product.id == filters.product_id)
            if filters.category_id:
                stmt = stmt.where(Product.category_id == filters.category_id)
            if filters.audience_id:
                stmt = stmt.where(Product.audience_id == filters.audience_id)
            if filters.item_status:
                stmt = stmt.where(ReservationItem.status == filters.item_status)

        if filters.search and filters.search.strip():
            term = f"%{filters.search.strip()}%"
            stmt = stmt.join(customer_search, customer_search.id == Reservation.customer_id)
            stmt = stmt.where(
                or_(
                    Reservation.reservation_code.ilike(term),
                    customer_search.first_name.ilike(term),
                    customer_search.last_name.ilike(term),
                    customer_search.email.ilike(term),
                )
            )

        reservations = db.scalars(stmt.distinct().order_by(Reservation.created_at.desc())).unique().all()

        rows: list[dict] = []
        status_counter: Counter[str] = Counter()
        total_units = 0
        estimated_total = Decimal("0")

        for reservation in reservations:
            names: list[str] = []
            item_statuses: set[str] = set()
            units = 0
            current_total = Decimal("0")
            for item in reservation.items:
                units += item.quantity
                current_total += Decimal(str(item.unit_price)) * item.quantity
                item_statuses.add(item.status)
                if item.product_variant and item.product_variant.product:
                    names.append(item.product_variant.product.name)

            status_counter[reservation.status] += 1
            total_units += units
            estimated_total += current_total

            rows.append(
                {
                    "reservation_code": reservation.reservation_code,
                    "date": reservation.created_at.isoformat(),
                    "branch": reservation.branch.name if reservation.branch else "—",
                    "customer": full_name(reservation.customer),
                    "status": reservation.status,
                    "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else None,
                    "products": ", ".join(dict.fromkeys(names)) or "—",
                    "items_quantity": units,
                    "estimated_total": money(current_total),
                    "item_statuses": ", ".join(sorted(item_statuses)) or "—",
                }
            )

        summary = {
            "reservations_count": len(rows),
            "units_reserved": total_units,
            "estimated_total": money(estimated_total),
            "by_status": dict(status_counter),
        }

        return report_payload(
            report_key="reservations",
            title="Reporte de reservas",
            filters=filters,
            summary=summary,
            columns=ReservationsReportService.COLUMNS,
            rows=rows,
        )

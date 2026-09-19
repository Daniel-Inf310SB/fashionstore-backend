from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import Depends, Query

from app.dependencies.permissions import require_permission
from app.models.user import User
from app.schemas.reports import (
    InventoryReportFilters,
    OrdersPaymentsReportFilters,
    ReservationsReportFilters,
    SalesReportFilters,
)


# =========================================================
# PERMISO DEL MÓDULO
# =========================================================

require_reports_view = require_permission("reports.view")


def get_reports_user(
    current_user: User = Depends(require_reports_view),
) -> User:
    return current_user


# =========================================================
# FILTROS - VENTAS
# =========================================================

def get_sales_report_filters(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    branch_id: int | None = Query(None, ge=1),
    customer_id: int | None = Query(None, ge=1),
    cashier_id: int | None = Query(None, ge=1),
    product_id: int | None = Query(None, ge=1),
    category_id: int | None = Query(None, ge=1),
    audience_id: int | None = Query(None, ge=1),
    payment_method: Literal["CASH", "CARD", "QR", "TRANSFER"] | None = Query(None),
    status: Literal["PENDING", "PAID", "CANCELLED", "REFUNDED"] | None = Query(None),
    min_total: Decimal | None = Query(None, ge=0),
    max_total: Decimal | None = Query(None, ge=0),
    search: str | None = Query(None, max_length=120),
) -> SalesReportFilters:
    return SalesReportFilters(
        date_from=date_from, date_to=date_to, branch_id=branch_id,
        customer_id=customer_id, cashier_id=cashier_id, product_id=product_id,
        category_id=category_id, audience_id=audience_id, payment_method=payment_method, status=status,
        min_total=min_total, max_total=max_total, search=search,
    )


# =========================================================
# FILTROS - INVENTARIO
# =========================================================

def get_inventory_report_filters(
    branch_id: int | None = Query(None, ge=1),
    product_id: int | None = Query(None, ge=1),
    category_id: int | None = Query(None, ge=1),
    audience_id: int | None = Query(None, ge=1),
    size_id: int | None = Query(None, ge=1),
    color_id: int | None = Query(None, ge=1),
    stock_state: Literal["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"] | None = Query(None),
    is_active: bool | None = Query(None),
    min_stock: int | None = Query(None, ge=0),
    max_stock: int | None = Query(None, ge=0),
    search: str | None = Query(None, max_length=120),
) -> InventoryReportFilters:
    return InventoryReportFilters(
        branch_id=branch_id, product_id=product_id, category_id=category_id, audience_id=audience_id,
        size_id=size_id, color_id=color_id, stock_state=stock_state,
        is_active=is_active, min_stock=min_stock, max_stock=max_stock,
        search=search,
    )


# =========================================================
# FILTROS - RESERVAS
# =========================================================

def get_reservations_report_filters(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    branch_id: int | None = Query(None, ge=1),
    customer_id: int | None = Query(None, ge=1),
    product_id: int | None = Query(None, ge=1),
    category_id: int | None = Query(None, ge=1),
    audience_id: int | None = Query(None, ge=1),
    status: Literal[
        "PENDING", "CONFIRMED", "PREPARING", "READY", "ATTENDED",
        "COMPLETED", "CANCELLED", "EXPIRED",
    ] | None = Query(None),
    item_status: Literal["PENDING", "RESERVED", "RELEASED", "CONSUMED"] | None = Query(None),
    search: str | None = Query(None, max_length=120),
) -> ReservationsReportFilters:
    return ReservationsReportFilters(
        date_from=date_from, date_to=date_to, branch_id=branch_id,
        customer_id=customer_id, product_id=product_id, category_id=category_id, audience_id=audience_id,
        status=status, item_status=item_status, search=search,
    )


# =========================================================
# FILTROS - COMPRAS Y PAGOS
# =========================================================

def get_orders_payments_report_filters(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    branch_id: int | None = Query(None, ge=1),
    customer_id: int | None = Query(None, ge=1),
    product_id: int | None = Query(None, ge=1),
    category_id: int | None = Query(None, ge=1),
    audience_id: int | None = Query(None, ge=1),
    order_status: Literal[
        "PENDING_PAYMENT", "PAYMENT_FAILED", "PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED",
        "DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED",
    ] | None = Query(None),
    payment_status: Literal[
        "PENDING", "PROCESSING", "APPROVED", "REJECTED", "FAILED", "CANCELLED", "REFUNDED",
    ] | None = Query(None),
    payment_method: Literal["CASH", "CARD", "QR", "TRANSFER"] | None = Query(None),
    delivery_type: Literal["PICKUP", "DELIVERY"] | None = Query(None),
    min_total: Decimal | None = Query(None, ge=0),
    max_total: Decimal | None = Query(None, ge=0),
    search: str | None = Query(None, max_length=120),
) -> OrdersPaymentsReportFilters:
    return OrdersPaymentsReportFilters(
        date_from=date_from, date_to=date_to, branch_id=branch_id,
        customer_id=customer_id, product_id=product_id, category_id=category_id, audience_id=audience_id,
        order_status=order_status, payment_status=payment_status,
        payment_method=payment_method, delivery_type=delivery_type,
        min_total=min_total, max_total=max_total, search=search,
    )

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DashboardBranchOption(BaseModel):
    id: int
    name: str


class DashboardScope(BaseModel):
    mode: str
    branch_id: int | None = None
    branch_name: str | None = None
    available_branches: list[DashboardBranchOption] = Field(default_factory=list)


class DashboardPeriod(BaseModel):
    date_from: date
    date_to: date
    previous_from: date
    previous_to: date


class DashboardKpis(BaseModel):
    revenue: Decimal
    pos_revenue: Decimal
    digital_revenue: Decimal
    revenue_change_pct: Decimal | None = None
    transactions_count: int
    transactions_change_pct: Decimal | None = None
    average_ticket: Decimal
    pos_sales_count: int
    digital_orders_count: int
    reservations_attention: int
    reservations_ready: int
    low_stock_variants: int
    out_of_stock_variants: int


class DashboardTrendPoint(BaseModel):
    date: date
    pos_revenue: Decimal
    digital_revenue: Decimal
    total_revenue: Decimal
    transactions: int


class DashboardTopProduct(BaseModel):
    product_id: int
    product_name: str
    units: int
    revenue: Decimal


class DashboardReservationStatus(BaseModel):
    status: str
    count: int


class DashboardInventoryItem(BaseModel):
    inventory_id: int
    branch_id: int
    branch_name: str
    product_id: int
    product_name: str
    sku: str
    available_quantity: int
    reorder_point: int
    stock_state: str


class DashboardBranchPerformance(BaseModel):
    branch_id: int
    branch_name: str
    revenue: Decimal
    transactions: int
    reservations_attention: int
    low_stock_variants: int


class DashboardActivityItem(BaseModel):
    type: str
    id: int
    code: str
    branch_id: int
    branch_name: str
    status: str
    amount: Decimal | None = None
    created_at: datetime


class DashboardResponse(BaseModel):
    generated_at: datetime
    scope: DashboardScope
    period: DashboardPeriod
    kpis: DashboardKpis
    sales_trend: list[DashboardTrendPoint]
    top_products: list[DashboardTopProduct]
    reservation_statuses: list[DashboardReservationStatus]
    low_stock: list[DashboardInventoryItem]
    branch_performance: list[DashboardBranchPerformance]
    recent_activity: list[DashboardActivityItem]

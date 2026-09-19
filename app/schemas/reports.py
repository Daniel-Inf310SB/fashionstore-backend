from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ExportFormat = Literal["pdf", "xlsx", "docx"]
StockState = Literal["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"]


class BaseDateFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from no puede ser posterior a date_to.")
        return self


class SalesReportFilters(BaseDateFilters):
    branch_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    cashier_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)
    audience_id: int | None = Field(default=None, ge=1)
    payment_method: Literal["CASH", "CARD", "QR", "TRANSFER"] | None = None
    status: Literal["PENDING", "PAID", "CANCELLED", "REFUNDED"] | None = None
    min_total: Decimal | None = Field(default=None, ge=0)
    max_total: Decimal | None = Field(default=None, ge=0)
    search: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_totals(self):
        if self.min_total is not None and self.max_total is not None and self.min_total > self.max_total:
            raise ValueError("min_total no puede ser mayor que max_total.")
        return self


class InventoryReportFilters(BaseModel):
    branch_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)
    audience_id: int | None = Field(default=None, ge=1)
    size_id: int | None = Field(default=None, ge=1)
    color_id: int | None = Field(default=None, ge=1)
    stock_state: StockState | None = None
    is_active: bool | None = None
    min_stock: int | None = Field(default=None, ge=0)
    max_stock: int | None = Field(default=None, ge=0)
    search: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_stock(self):
        if self.min_stock is not None and self.max_stock is not None and self.min_stock > self.max_stock:
            raise ValueError("min_stock no puede ser mayor que max_stock.")
        return self


class ReservationsReportFilters(BaseDateFilters):
    branch_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)
    audience_id: int | None = Field(default=None, ge=1)
    status: Literal[
        "PENDING", "CONFIRMED", "PREPARING", "READY", "ATTENDED",
        "COMPLETED", "CANCELLED", "EXPIRED",
    ] | None = None
    item_status: Literal["PENDING", "RESERVED", "RELEASED", "CONSUMED"] | None = None
    search: str | None = Field(default=None, max_length=120)


class OrdersPaymentsReportFilters(BaseDateFilters):
    branch_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)
    audience_id: int | None = Field(default=None, ge=1)
    order_status: Literal[
        "PENDING_PAYMENT", "PAYMENT_FAILED", "PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED",
        "DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED",
    ] | None = None
    payment_status: Literal[
        "PENDING", "PROCESSING", "APPROVED", "REJECTED", "FAILED", "CANCELLED", "REFUNDED",
    ] | None = None
    payment_method: Literal["CASH", "CARD", "QR", "TRANSFER"] | None = None
    delivery_type: Literal["PICKUP", "DELIVERY"] | None = None
    min_total: Decimal | None = Field(default=None, ge=0)
    max_total: Decimal | None = Field(default=None, ge=0)
    search: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_totals(self):
        if self.min_total is not None and self.max_total is not None and self.min_total > self.max_total:
            raise ValueError("min_total no puede ser mayor que max_total.")
        return self


class ReportColumn(BaseModel):
    key: str
    label: str


class ReportResponse(BaseModel):
    report_key: str
    title: str
    generated_at: datetime
    filters: dict[str, Any]
    summary: dict[str, Any]
    columns: list[ReportColumn]
    rows: list[dict[str, Any]]
    total_rows: int

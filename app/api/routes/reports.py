from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.reports import (
    get_inventory_report_filters,
    get_orders_payments_report_filters,
    get_reports_user,
    get_reservations_report_filters,
    get_sales_report_filters,
)
from app.models.user import User
from app.schemas.report_assistant import ReportAssistantRequest, ReportAssistantResponse
from app.schemas.reports import (
    InventoryReportFilters,
    OrdersPaymentsReportFilters,
    ReportResponse,
    ReservationsReportFilters,
    SalesReportFilters,
)
from app.services.reports.export_service import ReportExportService
from app.services.reports.inventory_report_service import InventoryReportService
from app.services.reports.orders_payments_report_service import OrdersPaymentsReportService
from app.services.reports.reservations_report_service import ReservationsReportService
from app.services.reports.sales_report_service import SalesReportService
from app.services.reports.report_assistant_service import ReportAssistantService


router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)

ExportFormat = Literal["pdf", "xlsx", "docx"]


def _handle_error(exc: Exception):
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    raise exc


def _download(report: dict, export_format: ExportFormat) -> Response:
    content, media_type, extension = ReportExportService.export(report, export_format)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"fashionstore_{report['report_key']}_{stamp}.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )




# =========================================================
# ASISTENTE IA - COMANDOS DE TEXTO / VOZ
# =========================================================

@router.post("/assistant/interpret", response_model=ReportAssistantResponse)
def interpret_report_command(
    payload: ReportAssistantRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return ReportAssistantService.interpret(db, payload)
    except Exception as exc:
        _handle_error(exc)

# =========================================================
# REPORTE 1 - VENTAS
# =========================================================

@router.get("/sales", response_model=ReportResponse)
def sales_report(
    filters: SalesReportFilters = Depends(get_sales_report_filters),
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return SalesReportService.build(db, filters)
    except Exception as exc:
        _handle_error(exc)


@router.get("/sales/export")
def export_sales_report(
    format: ExportFormat = Query(...),
    filters: SalesReportFilters = Depends(get_sales_report_filters),
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return _download(SalesReportService.build(db, filters), format)
    except Exception as exc:
        _handle_error(exc)


# =========================================================
# REPORTE 2 - INVENTARIO
# =========================================================

@router.get("/inventory", response_model=ReportResponse)
def inventory_report(
    filters: InventoryReportFilters = Depends(get_inventory_report_filters),
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return InventoryReportService.build(db, filters)
    except Exception as exc:
        _handle_error(exc)


@router.get("/inventory/export")
def export_inventory_report(
    format: ExportFormat = Query(...),
    filters: InventoryReportFilters = Depends(get_inventory_report_filters),
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return _download(InventoryReportService.build(db, filters), format)
    except Exception as exc:
        _handle_error(exc)


# =========================================================
# REPORTE 3 - RESERVAS
# =========================================================

@router.get("/reservations", response_model=ReportResponse)
def reservations_report(
    filters: ReservationsReportFilters = Depends(get_reservations_report_filters),
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return ReservationsReportService.build(db, filters)
    except Exception as exc:
        _handle_error(exc)


@router.get("/reservations/export")
def export_reservations_report(
    format: ExportFormat = Query(...),
    filters: ReservationsReportFilters = Depends(get_reservations_report_filters),
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return _download(ReservationsReportService.build(db, filters), format)
    except Exception as exc:
        _handle_error(exc)


# =========================================================
# REPORTE 4 - COMPRAS DIGITALES Y PAGOS
# =========================================================

@router.get("/orders-payments", response_model=ReportResponse)
def orders_payments_report(
    filters: OrdersPaymentsReportFilters = Depends(get_orders_payments_report_filters),
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return OrdersPaymentsReportService.build(db, filters)
    except Exception as exc:
        _handle_error(exc)


@router.get("/orders-payments/export")
def export_orders_payments_report(
    format: ExportFormat = Query(...),
    filters: OrdersPaymentsReportFilters = Depends(get_orders_payments_report_filters),
    db: Session = Depends(get_db),
    _: User = Depends(get_reports_user),
):
    try:
        return _download(OrdersPaymentsReportService.build(db, filters), format)
    except Exception as exc:
        _handle_error(exc)

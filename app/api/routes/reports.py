from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.plan_features import require_plan_feature
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
    CashReconciliationFilters,
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
from app.services.reports.cash_reconciliation_service import CashReconciliationService
from app.services.reports.sales_report_service import SalesReportService
from app.services.reports.sales_analysis_service import SalesAnalysisService
from app.services.reports.report_assistant_service import ReportAssistantService
from app.services.ai.report_audio_transcription import transcribe_report_audio


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
    user: User = Depends(get_reports_user),
    __: User = Depends(require_plan_feature("ai_reports")),
):
    try:
        return ReportAssistantService.interpret(db, payload, tenant_id=user.tenant_id)
    except Exception as exc:
        _handle_error(exc)


@router.post("/assistant/transcribe")
async def transcribe_report_command_audio(
    request: Request,
    user: User = Depends(get_reports_user),
    _: User = Depends(require_plan_feature("ai_reports")),
):
    """Transcribe audio, sin ejecutar instrucciones ni modificar datos."""
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    allowed = {"audio/webm", "audio/mp4", "audio/mpeg", "audio/wav", "audio/ogg"}
    if content_type not in allowed:
        raise HTTPException(415, "Formato de audio no admitido.")
    if request.headers.get("content-length", "").isdigit() and int(request.headers["content-length"]) > 4_000_000:
        raise HTTPException(413, "La grabación supera el límite de 4 MB.")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 4_000_000:
            raise HTTPException(413, "La grabación supera el límite de 4 MB.")
    if len(data) < 1500:
        raise HTTPException(400, "La grabación es demasiado corta o está vacía.")
    try:
        text = await transcribe_report_audio(bytes(data), content_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"text": text}

# =========================================================
# CU77 - CONCILIACION DE INGRESOS DE CAJA
# =========================================================

@router.get("/cash/reconciliation", response_model=ReportResponse)
def cash_reconciliation_report(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    branch_id: int | None = Query(None, ge=1),
    cashier_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        filters = CashReconciliationFilters(date_from=date_from, date_to=date_to,
                                            branch_id=branch_id, cashier_id=cashier_id)
        return CashReconciliationService.build(db, filters, tenant_id=user.tenant_id)
    except Exception as exc:
        _handle_error(exc)


@router.get("/cash/reconciliation/export")
def export_cash_reconciliation(
    format: ExportFormat = Query(...),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    branch_id: int | None = Query(None, ge=1),
    cashier_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        filters = CashReconciliationFilters(date_from=date_from, date_to=date_to,
                                            branch_id=branch_id, cashier_id=cashier_id)
        return _download(CashReconciliationService.build(db, filters, tenant_id=user.tenant_id), format)
    except Exception as exc:
        _handle_error(exc)


# =========================================================
# REPORTE 1 - VENTAS
# =========================================================

@router.get("/sales", response_model=ReportResponse)
def sales_report(
    filters: SalesReportFilters = Depends(get_sales_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        return SalesReportService.build(db, filters, tenant_id=user.tenant_id)
    except Exception as exc:
        _handle_error(exc)


@router.get("/sales/export")
def export_sales_report(
    format: ExportFormat = Query(...),
    filters: SalesReportFilters = Depends(get_sales_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        return _download(SalesReportService.build(db, filters, tenant_id=user.tenant_id), format)
    except Exception as exc:
        _handle_error(exc)


@router.get("/sales/analysis", response_model=ReportResponse)
def sales_analysis(
    kind: Literal["top_products", "branch_comparison", "weekly_sales", "category_revenue"] = Query(...),
    limit: int = Query(10, ge=1, le=100),
    filters: SalesReportFilters = Depends(get_sales_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
    __: User = Depends(require_plan_feature("ai_reports")),
):
    try:
        return SalesAnalysisService.build(db, filters, tenant_id=user.tenant_id, kind=kind, limit=limit)
    except Exception as exc:
        _handle_error(exc)


@router.get("/sales/analysis/export")
def export_sales_analysis(
    kind: Literal["top_products", "branch_comparison", "weekly_sales", "category_revenue"] = Query(...),
    format: ExportFormat = Query(...),
    limit: int = Query(10, ge=1, le=100),
    filters: SalesReportFilters = Depends(get_sales_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
    __: User = Depends(require_plan_feature("ai_reports")),
):
    try:
        return _download(SalesAnalysisService.build(db, filters, tenant_id=user.tenant_id, kind=kind, limit=limit), format)
    except Exception as exc:
        _handle_error(exc)


# =========================================================
# REPORTE 2 - INVENTARIO
# =========================================================

@router.get("/inventory", response_model=ReportResponse)
def inventory_report(
    filters: InventoryReportFilters = Depends(get_inventory_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        return InventoryReportService.build(db, filters, tenant_id=user.tenant_id)
    except Exception as exc:
        _handle_error(exc)


@router.get("/inventory/export")
def export_inventory_report(
    format: ExportFormat = Query(...),
    filters: InventoryReportFilters = Depends(get_inventory_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        return _download(InventoryReportService.build(db, filters, tenant_id=user.tenant_id), format)
    except Exception as exc:
        _handle_error(exc)


# =========================================================
# REPORTE 3 - RESERVAS
# =========================================================

@router.get("/reservations", response_model=ReportResponse)
def reservations_report(
    filters: ReservationsReportFilters = Depends(get_reservations_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        return ReservationsReportService.build(db, filters, tenant_id=user.tenant_id)
    except Exception as exc:
        _handle_error(exc)


@router.get("/reservations/export")
def export_reservations_report(
    format: ExportFormat = Query(...),
    filters: ReservationsReportFilters = Depends(get_reservations_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        return _download(ReservationsReportService.build(db, filters, tenant_id=user.tenant_id), format)
    except Exception as exc:
        _handle_error(exc)


# =========================================================
# REPORTE 4 - COMPRAS DIGITALES Y PAGOS
# =========================================================

@router.get("/orders-payments", response_model=ReportResponse)
def orders_payments_report(
    filters: OrdersPaymentsReportFilters = Depends(get_orders_payments_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        return OrdersPaymentsReportService.build(db, filters, tenant_id=user.tenant_id)
    except Exception as exc:
        _handle_error(exc)


@router.get("/orders-payments/export")
def export_orders_payments_report(
    format: ExportFormat = Query(...),
    filters: OrdersPaymentsReportFilters = Depends(get_orders_payments_report_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_reports_user),
):
    try:
        return _download(OrdersPaymentsReportService.build(db, filters, tenant_id=user.tenant_id), format)
    except Exception as exc:
        _handle_error(exc)

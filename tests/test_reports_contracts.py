"""Pruebas unitarias de contrato de los cuatro reportes (sin PostgreSQL)."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from app.api.routes import reports as routes
from app.schemas.reports import (
    SalesReportFilters, InventoryReportFilters,
    ReservationsReportFilters, OrdersPaymentsReportFilters,
)

REPORT_CASES = [
    ("sales", routes.sales_report, routes.export_sales_report, routes.SalesReportService, SalesReportFilters),
    ("inventory", routes.inventory_report, routes.export_inventory_report, routes.InventoryReportService, InventoryReportFilters),
    ("reservations", routes.reservations_report, routes.export_reservations_report, routes.ReservationsReportService, ReservationsReportFilters),
    ("orders-payments", routes.orders_payments_report, routes.export_orders_payments_report, routes.OrdersPaymentsReportService, OrdersPaymentsReportFilters),
]

@pytest.mark.parametrize("key,read,export,service,filters_type", REPORT_CASES, ids=[c[0] for c in REPORT_CASES])
def test_report_service_receives_authenticated_tenant_and_filters(key, read, export, service, filters_type):
    db = object()
    filters = filters_type(branch_id=31)
    user = SimpleNamespace(tenant_id=2)
    expected = {"report_key": key, "rows": [], "total_rows": 0}
    with patch.object(service, "build", return_value=expected) as build:
        result = read(filters=filters, db=db, user=user)
    assert result == expected
    build.assert_called_once_with(db, filters, tenant_id=2)

@pytest.mark.parametrize("key,read,export,service,filters_type", REPORT_CASES, ids=[c[0] for c in REPORT_CASES])
@pytest.mark.parametrize("format", ["pdf", "xlsx", "docx"])
def test_export_uses_same_tenant_filters_and_report(key, read, export, service, filters_type, format):
    db = object()
    filters = filters_type(branch_id=31)
    user = SimpleNamespace(tenant_id=3)
    expected = {"report_key": key, "rows": [], "total_rows": 0}
    with patch.object(service, "build", return_value=expected) as build, patch.object(routes, "_download", return_value=b"file") as download:
        result = export(format=format, filters=filters, db=db, user=user)
    assert result == b"file"
    build.assert_called_once_with(db, filters, tenant_id=3)
    download.assert_called_once_with(expected, format)

@pytest.mark.parametrize("filters_type", [SalesReportFilters, ReservationsReportFilters, OrdersPaymentsReportFilters])
def test_date_range_rejects_inverted_period(filters_type):
    with pytest.raises(ValueError):
        filters_type(date_from="2026-10-18", date_to="2026-10-01")

"""Cash-desk reconciliation: original sale payments and exchange top-ups once each.

This is a reporting projection, not a payment ledger mutation.
"""
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.sale import Sale
from app.models.sale_exchange import SaleExchange
from app.schemas.reports import CashReconciliationFilters
from app.services.reports.base import end_of_day, money, report_payload, start_of_day


class CashReconciliationService:
    COLUMNS = [
        {"key": "date", "label": "Fecha"},
        {"key": "operation", "label": "Tipo de ingreso"},
        {"key": "reference", "label": "Comprobante"},
        {"key": "sale_code", "label": "Venta original"},
        {"key": "branch_id", "label": "Sucursal"},
        {"key": "cashier_id", "label": "Cajero"},
        {"key": "method", "label": "Método"},
        {"key": "amount", "label": "Ingreso (Bs)"},
    ]

    @staticmethod
    def build(db: Session, filters: CashReconciliationFilters, *, tenant_id: int) -> dict:
        beginning, ending = start_of_day(filters.date_from), end_of_day(filters.date_to)
        sales_stmt = (
            select(Payment, Sale)
            .join(Sale, Payment.sale_id == Sale.id)
            .where(Sale.tenant_id == tenant_id, Payment.channel == "CASH_DESK", Payment.status == "APPROVED")
        )
        if filters.branch_id:
            sales_stmt = sales_stmt.where(Sale.branch_id == filters.branch_id)
        if filters.cashier_id:
            sales_stmt = sales_stmt.where(Sale.cashier_id == filters.cashier_id)
        if beginning:
            sales_stmt = sales_stmt.where(Payment.paid_at >= beginning)
        if ending:
            sales_stmt = sales_stmt.where(Payment.paid_at <= ending)

        exchange_stmt = (
            select(SaleExchange, Sale.sale_code)
            .join(Sale, Sale.id == SaleExchange.sale_id)
            .where(SaleExchange.tenant_id == tenant_id,
                   Sale.tenant_id == tenant_id,
                   SaleExchange.additional_paid > 0,
                   SaleExchange.payment_method == "CASH")
        )
        if filters.branch_id:
            exchange_stmt = exchange_stmt.where(SaleExchange.branch_id == filters.branch_id)
        if filters.cashier_id:
            exchange_stmt = exchange_stmt.where(SaleExchange.cashier_id == filters.cashier_id)
        if beginning:
            exchange_stmt = exchange_stmt.where(SaleExchange.created_at >= beginning)
        if ending:
            exchange_stmt = exchange_stmt.where(SaleExchange.created_at <= ending)

        rows = []
        sale_total = Decimal("0.00")
        exchange_total = Decimal("0.00")
        for payment, sale in db.execute(sales_stmt).all():
            amount = Decimal(str(payment.amount))
            sale_total += amount
            rows.append({
                "date": (payment.paid_at or payment.created_at).isoformat(),
                "operation": "COBRO_VENTA", "reference": payment.payment_code,
                "sale_code": sale.sale_code, "branch_id": sale.branch_id,
                "cashier_id": sale.cashier_id, "method": payment.payment_method,
                "amount": money(amount),
            })
        for exchange, sale_code in db.execute(exchange_stmt).all():
            amount = Decimal(str(exchange.additional_paid))
            exchange_total += amount
            rows.append({
                "date": exchange.created_at.isoformat(),
                "operation": "DIFERENCIA_CAMBIO", "reference": exchange.exchange_code,
                "sale_code": sale_code, "branch_id": exchange.branch_id,
                "cashier_id": exchange.cashier_id, "method": "CASH", "amount": money(amount),
            })
        rows.sort(key=lambda row: row["date"], reverse=True)
        return report_payload(
            report_key="cash_reconciliation", title="Ingresos de caja: ventas y cambios",
            filters=filters,
            summary={
                "sale_payments_total": money(sale_total),
                "exchange_topups_total": money(exchange_total),
                "cash_desk_income_total": money(sale_total + exchange_total),
                "sale_payment_count": sum(r["operation"] == "COBRO_VENTA" for r in rows),
                "exchange_topup_count": sum(r["operation"] == "DIFERENCIA_CAMBIO" for r in rows),
                "note": "Cobros aprobados de caja y diferencias positivas de cambios; cada operación se cuenta una sola vez. No incluye egresos ni cierre físico de caja.",
            },
            columns=CashReconciliationService.COLUMNS, rows=rows,
        )

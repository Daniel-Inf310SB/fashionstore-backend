"""Conciliación de cobros Stripe sin depender de webhooks ni del móvil.

Solo se confirma un intento tras consultar Stripe, validar sus datos e impedir
que dos trabajadores apliquen la misma compra simultáneamente.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.database.session import SessionLocal
from app.models.order import Order
from app.models.payment import Payment
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.receipt_service import ReceiptService
from app.services.stripe_service import StripeGateway

logger = logging.getLogger(__name__)


def run_stripe_reconciliation_jobs(batch_size: int = 25) -> None:
    if batch_size < 1:
        return
    # El scheduler no debe sostener una transacción mientras llama a Stripe.
    with SessionLocal() as db:
        candidate_ids = [p.id for p in db.query(Payment.id).filter(
            Payment.provider == "STRIPE",
            Payment.status.in_(("PENDING", "PROCESSING")),
            Payment.external_transaction_id.isnot(None),
            Payment.order_id.isnot(None),
        ).order_by(Payment.id.asc()).limit(batch_size).all()]
        db.rollback()

    for payment_id in candidate_ids:
        reconcile_one_stripe_payment(payment_id)


def reconcile_one_stripe_payment(payment_id: int) -> bool:
    """Consulta Stripe y confirma un pago comprobado; nunca acepta el estado del móvil."""
    try:
        with SessionLocal() as db:
            candidate = db.query(Payment).filter(Payment.id == payment_id).first()
            if candidate is None or candidate.status not in {"PENDING", "PROCESSING"}:
                return False
            intent_id = candidate.external_transaction_id
            db.rollback()
            if not intent_id:
                return False

        intent = StripeGateway.retrieve_payment_intent(intent_id)
        if getattr(intent, "status", None) != "succeeded":
            return False

        issue_receipt = None
        with SessionLocal() as db:
            payment = db.query(Payment).filter(Payment.id == payment_id).with_for_update().first()
            if payment is None or payment.status not in {"PENDING", "PROCESSING"}:
                return False
            if payment.provider != "STRIPE" or payment.external_transaction_id != getattr(intent, "id", None):
                raise ValueError("El PaymentIntent no coincide con el intento local")
            order = db.query(Order).filter(Order.id == payment.order_id).with_for_update().first()
            if order is None:
                raise ValueError("Compra no encontrada")
            # No confirmar pedidos cancelados o reembolsados automáticamente:
            # requieren conciliación manual, especialmente si se liberó stock.
            if order.status not in {"PENDING_PAYMENT", "PAYMENT_FAILED"}:
                if order.status not in {"PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED", "DELIVERED", "COMPLETED"}:
                    raise ValueError(f"Pedido {order.id} en estado {order.status}; revisión manual")
                # Si ya fue completado por otro evento, sincronizar solo el pago.
            # Stripe entrega metadata como StripeObject, no como dict.
            # Convertir antes de usar .get() (manteniendo las validaciones).
            raw_metadata = getattr(intent, "metadata", None)
            if hasattr(raw_metadata, "to_dict"):
                metadata = raw_metadata.to_dict()
            elif isinstance(raw_metadata, dict):
                metadata = raw_metadata
            else:
                metadata = {}
            if (str(metadata.get("order_id", "")) != str(order.id)
                    or metadata.get("order_code") != order.order_code
                    or metadata.get("payment_code") != payment.payment_code):
                raise ValueError("Los metadatos de Stripe no corresponden al pedido")
            if (str(getattr(intent, "currency", "")).upper() != str(payment.currency).upper()
                    or StripeGateway.amount_to_minor_units(payment.amount) != int(getattr(intent, "amount_received", -1))
                    or StripeGateway.amount_to_minor_units(order.total_amount) != int(getattr(intent, "amount_received", -1))):
                raise ValueError("Monto o moneda de Stripe diferentes del pedido")
            previous_status = payment.status
            payment.status = "APPROVED"
            payment.failure_reason = None
            payment.paid_at = payment.paid_at or datetime.now(timezone.utc)
            OrderService.mark_paid_from_payment(db, order=order, payment=payment)
            PaymentService._audit(
                db, current_user=None, payment=payment, action="STRIPE_API_RECONCILE",
                description=f"Pago {payment.payment_code} validado directamente con Stripe",
                old_status=previous_status,
            )
            db.commit()
            issue_receipt = (order.id, payment.id)
            logger.info("[STRIPE RECONCILE] pedido=%s pago=%s APPROVED", order.id, payment.id)

        if issue_receipt:
            try:
                with SessionLocal() as db:
                    ReceiptService.issue_and_email_order_receipt(
                        db, order_id=issue_receipt[0], payment_id=issue_receipt[1]
                    )
            except Exception:
                logger.exception("[STRIPE RECONCILE] Falló comprobante (pago persistido)")
        return True
    except Exception:
        logger.exception("[STRIPE RECONCILE] No se pudo conciliar payment_id=%s", payment_id)
        return False

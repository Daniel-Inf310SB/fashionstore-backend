from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.order import Order
from app.models.payment import Payment
from app.models.reservation import Reservation
from app.services.order_service import OrderService
from app.services.notification_service import NotificationService
from app.services.reservation_service import ReservationService
from app.services.stripe_service import StripeGateway


class ExpirationService:
    """Expiración automática de compras y reservas.

    El scheduler llama estos métodos periódicamente y las rutas GET los usan
    también como comprobación defensiva. Todos los cambios importantes se
    vuelven a validar con bloqueo de fila antes de modificarse.
    """

    ORDER_EXPIRABLE_STATUSES = {"PENDING_PAYMENT", "PAYMENT_FAILED"}
    ORDER_ACTIVE_PAYMENT_STATUSES = {"PENDING", "PROCESSING"}

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    # =====================================================
    # COMPRAS DIGITALES
    # =====================================================

    @staticmethod
    def expire_due_orders(db: Session) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=settings.order_payment_ttl_minutes
        )

        order_ids = [
            row[0]
            for row in (
                db.query(Order.id)
                .filter(
                    Order.status.in_(
                        ExpirationService.ORDER_EXPIRABLE_STATUSES
                    ),
                    Order.created_at <= cutoff,
                )
                .order_by(Order.id.asc())
                .all()
            )
        ]

        expired = 0
        reconciled_paid = 0
        skipped = 0

        for order_id in order_ids:
            try:
                result = ExpirationService.expire_order_if_needed(
                    db,
                    order_id=order_id,
                )
            except Exception as exc:
                # Una compra antigua/inconsistente no debe tumbar todo el
                # historial del cliente ni el job completo. Se revierte solo
                # esta iteración y se continúa con las demás órdenes.
                db.rollback()
                skipped += 1
                print(
                    f"[EXPIRATION][ORDER] Se omitió la orden {order_id}: {exc}"
                )
                continue

            if result == "EXPIRED":
                expired += 1
            elif result == "PAID":
                reconciled_paid += 1
            elif result == "SKIPPED":
                skipped += 1

        return {
            "checked": len(order_ids),
            "expired": expired,
            "reconciled_paid": reconciled_paid,
            "skipped": skipped,
        }

    @staticmethod
    def expire_order_if_needed(
        db: Session,
        *,
        order_id: int,
    ) -> str:
        order = (
            db.query(Order)
            .filter(Order.id == order_id)
            .with_for_update()
            .first()
        )

        if order is None:
            db.rollback()
            return "SKIPPED"

        if order.status not in ExpirationService.ORDER_EXPIRABLE_STATUSES:
            db.rollback()
            return "SKIPPED"

        created_at = ExpirationService._as_utc(order.created_at)
        expires_at = created_at + timedelta(
            minutes=settings.order_payment_ttl_minutes
        )

        if expires_at > datetime.now(timezone.utc):
            db.rollback()
            return "SKIPPED"

        # Si por alguna razón el webhook confirmó el Payment pero la orden
        # todavía no cambió, reconciliamos antes de intentar expirar.
        approved_payment = (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id,
                Payment.provider == "STRIPE",
                Payment.status == "APPROVED",
            )
            .order_by(Payment.id.desc())
            .first()
        )

        if approved_payment is not None:
            try:
                OrderService.mark_paid_from_payment(
                    db,
                    order=order,
                    payment=approved_payment,
                )
                db.commit()
                return "PAID"
            except Exception:
                db.rollback()
                raise

        active_payments = (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id,
                Payment.provider == "STRIPE",
                Payment.status.in_(
                    ExpirationService.ORDER_ACTIVE_PAYMENT_STATUSES
                ),
            )
            .order_by(Payment.id.asc())
            .all()
        )

        try:
            for payment in active_payments:
                old_status = payment.status

                if not payment.external_transaction_id:
                    payment.status = "CANCELLED"
                    payment.failure_reason = (
                        "Intento cancelado por vencimiento del tiempo de pago."
                    )
                    continue

                try:
                    intent = StripeGateway.retrieve_payment_intent(
                        payment.external_transaction_id
                    )
                except Exception as exc:
                    # Si no podemos verificar Stripe, no liberamos stock.
                    # Es más seguro conservar la compra pendiente.
                    db.rollback()
                    return "SKIPPED"

                stripe_status = getattr(intent, "status", None)

                if stripe_status == "succeeded":
                    payment.status = "APPROVED"
                    payment.paid_at = payment.paid_at or datetime.now(
                        timezone.utc
                    )
                    payment.failure_reason = None

                    OrderService.mark_paid_from_payment(
                        db,
                        order=order,
                        payment=payment,
                    )

                    db.add(
                        AuditLog(
                            user_id=payment.user_id,
                            action="RECONCILE_EXPIRED_ORDER_PAYMENT",
                            module="PAYMENTS",
                            entity_type="Payment",
                            entity_id=payment.id,
                            description=(
                                "Stripe ya había confirmado el pago al revisar "
                                f"la expiración de {order.order_code}."
                            ),
                            old_values={"status": old_status},
                            new_values={"status": "APPROVED"},
                            status="SUCCESS",
                        )
                    )

                    db.commit()
                    return "PAID"

                if stripe_status == "canceled":
                    payment.status = "CANCELLED"
                    payment.failure_reason = (
                        "Stripe informó que el intento estaba cancelado."
                    )
                    continue

                # Para requires_payment_method, requires_confirmation,
                # requires_action y processing intentamos cancelar en Stripe.
                try:
                    StripeGateway.cancel_payment_intent(
                        payment.external_transaction_id
                    )
                except Exception:
                    # Puede haber una carrera con un pago que acaba de
                    # completarse. No liberamos stock si Stripe no confirmó
                    # la cancelación.
                    db.rollback()
                    return "SKIPPED"

                payment.status = "CANCELLED"
                payment.failure_reason = (
                    "Intento cancelado por vencimiento del tiempo de pago."
                )

            OrderService._release_reserved_inventory(
                db,
                order=order,
                user_id=None,
                reason=(
                    "Reserva liberada por vencimiento del tiempo de pago "
                    "de la compra digital."
                ),
            )

            old_order_status = order.status
            order.status = "CANCELLED"
            order.cancelled_at = datetime.now(timezone.utc)

            NotificationService.notify_order_status(
                db,
                order=order,
                status="CANCELLED",
                reason="Venció el tiempo disponible para completar el pago.",
            )

            db.add(
                AuditLog(
                    user_id=None,
                    action="AUTO_EXPIRE_ORDER",
                    module="ORDERS",
                    entity_type="Order",
                    entity_id=order.id,
                    description=(
                        f"Compra {order.order_code} cancelada automáticamente "
                        "por vencimiento del tiempo de pago."
                    ),
                    old_values={"status": old_order_status},
                    new_values={
                        "status": "CANCELLED",
                        "reason": "PAYMENT_TIMEOUT",
                    },
                    status="SUCCESS",
                )
            )

            db.commit()
            return "EXPIRED"

        except Exception:
            db.rollback()
            raise

    # =====================================================
    # RESERVAS
    # =====================================================

    @staticmethod
    def expire_due_reservations(db: Session) -> dict:
        now = datetime.now(timezone.utc)

        # Solo pueden vencer reservas cuyo plazo ya empezó.
        # PENDING no forma parte de EXPIRABLE_STATUSES y no tiene
        # expires_at; el plazo se asigna al confirmar.
        reservation_ids = [
            row[0]
            for row in (
                db.query(Reservation.id)
                .filter(
                    Reservation.status.in_(
                        ReservationService.EXPIRABLE_STATUSES
                    ),
                    Reservation.expires_at.is_not(None),
                    Reservation.expires_at <= now,
                )
                .order_by(Reservation.id.asc())
                .all()
            )
        ]

        expired = 0
        skipped = 0

        for reservation_id in reservation_ids:
            if ExpirationService.expire_reservation_if_needed(
                db,
                reservation_id=reservation_id,
            ):
                expired += 1
            else:
                skipped += 1

        return {
            "checked": len(reservation_ids),
            "expired": expired,
            "skipped": skipped,
        }

    @staticmethod
    def expire_reservation_if_needed(
        db: Session,
        *,
        reservation_id: int,
    ) -> bool:
        reservation = (
            db.query(Reservation)
            .filter(Reservation.id == reservation_id)
            .with_for_update()
            .first()
        )

        if reservation is None:
            db.rollback()
            return False

        if reservation.status not in ReservationService.EXPIRABLE_STATUSES:
            db.rollback()
            return False

        now = datetime.now(timezone.utc)

        # Una reserva sin expires_at todavía no inició su plazo de
        # retiro (normalmente sigue PENDING o es un dato legado).
        if reservation.expires_at is None:
            db.rollback()
            return False

        expires_at = ExpirationService._as_utc(reservation.expires_at)

        if expires_at > now:
            db.rollback()
            return False

        # expire_reservation vuelve a cargar la entidad. Liberamos el bloqueo
        # actual antes de reutilizar la lógica consolidada del módulo.
        db.rollback()

        ReservationService.expire_reservation(
            db,
            reservation_id=reservation_id,
            system_user_id=None,
        )
        return True

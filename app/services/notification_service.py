from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.services.push_notification_service import PushNotificationService


class NotificationService:
    """Notificaciones persistidas + outbox push transaccional."""

    @staticmethod
    def create(
        db: Session,
        *,
        user_id: int,
        notification_type: str,
        event: str,
        title: str,
        message: str,
        entity_type: str | None = None,
        entity_id: int | None = None,
        action_url: str | None = None,
        dedupe_key: str | None = None,
    ) -> Notification:
        if dedupe_key:
            existing = (
                db.query(Notification)
                .filter(Notification.dedupe_key == dedupe_key)
                .first()
            )
            if existing is not None:
                return existing

        notification = Notification(
            user_id=user_id,
            type=notification_type,
            event=event,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
            dedupe_key=dedupe_key,
            is_read=False,
        )
        db.add(notification)

        # Necesitamos el ID para construir las entregas push.
        # El flush participa en la transacción actual: NO hace commit.
        db.flush()

        PushNotificationService.enqueue_for_notification(
            db,
            notification=notification,
        )

        return notification

    @staticmethod
    def notify_order_status(
        db: Session,
        *,
        order,
        status: str,
        reason: str | None = None,
    ) -> Notification | None:
        messages = {
            "PAID": (
                "Pago confirmado",
                f"El pago de tu pedido {order.order_code} fue confirmado correctamente.",
            ),
            "PAYMENT_FAILED": (
                "No pudimos procesar tu pago",
                f"El pago de tu pedido {order.order_code} no pudo completarse. Puedes volver a intentarlo.",
            ),
            "PREPARING": (
                "Estamos preparando tu pedido",
                f"Tu pedido {order.order_code} ya está siendo preparado por la sucursal.",
            ),
            "READY_FOR_PICKUP": (
                "Tu pedido está listo para recoger",
                f"Tu pedido {order.order_code} ya está listo para recoger en la sucursal seleccionada.",
            ),
            "SHIPPED": (
                "Tu pedido fue enviado",
                f"Tu pedido {order.order_code} salió de la sucursal y está en camino.",
            ),
            "DELIVERED": (
                "Pedido entregado",
                f"Tu pedido {order.order_code} fue marcado como entregado.",
            ),
            "COMPLETED": (
                "Pedido finalizado",
                f"Tu pedido {order.order_code} fue completado correctamente.",
            ),
            "CANCELLED": (
                "Pedido cancelado",
                f"Tu pedido {order.order_code} fue cancelado."
                + (f" Motivo: {reason}" if reason else ""),
            ),
            "REFUNDED": (
                "Pago reembolsado",
                f"El pago de tu pedido {order.order_code} fue reembolsado.",
            ),
        }

        content = messages.get(status)
        if content is None:
            return None

        title, message = content

        return NotificationService.create(
            db,
            user_id=order.customer_id,
            notification_type="ORDER",
            event=f"ORDER_{status}",
            title=title,
            message=message,
            entity_type="ORDER",
            entity_id=order.id,
            action_url=f"/orders/{order.id}",
            dedupe_key=f"ORDER:{order.id}:{status}",
        )

    @staticmethod
    def notify_reservation_status(
        db: Session,
        *,
        reservation,
        status: str,
        reason: str | None = None,
    ) -> Notification | None:
        messages = {
            "CONFIRMED": (
                "Reserva confirmada",
                f"Tu reserva {reservation.reservation_code} fue confirmada por la sucursal.",
            ),
            "PREPARING": (
                "Estamos preparando tu reserva",
                f"La sucursal comenzó a preparar tu reserva {reservation.reservation_code}.",
            ),
            "READY": (
                "Tu reserva está lista",
                f"Tu reserva {reservation.reservation_code} está lista para ser atendida en la sucursal.",
            ),
            "ATTENDED": (
                "Reserva atendida",
                f"Tu reserva {reservation.reservation_code} fue marcada como atendida.",
            ),
            "COMPLETED": (
                "Reserva completada",
                f"Tu reserva {reservation.reservation_code} fue completada correctamente.",
            ),
            "CANCELLED": (
                "Reserva cancelada",
                f"Tu reserva {reservation.reservation_code} fue cancelada."
                + (f" Motivo: {reason}" if reason else ""),
            ),
            "EXPIRED": (
                "Tu reserva venció",
                f"Tu reserva {reservation.reservation_code} venció y las prendas fueron liberadas.",
            ),
        }

        content = messages.get(status)
        if content is None:
            return None

        title, message = content

        return NotificationService.create(
            db,
            user_id=reservation.customer_id,
            notification_type="RESERVATION",
            event=f"RESERVATION_{status}",
            title=title,
            message=message,
            entity_type="RESERVATION",
            entity_id=reservation.id,
            action_url=f"/reservations/{reservation.id}",
            dedupe_key=f"RESERVATION:{reservation.id}:{status}",
        )

    @staticmethod
    def list_my_notifications(
        db: Session,
        *,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        is_read: bool | None = None,
        notification_type: str | None = None,
    ) -> dict:
        page = max(page, 1)
        page_size = max(1, min(page_size, 100))

        query = db.query(Notification).filter(Notification.user_id == user_id)

        if is_read is not None:
            query = query.filter(Notification.is_read.is_(is_read))

        if notification_type:
            query = query.filter(Notification.type == notification_type)

        total = query.order_by(None).count()

        unread_count = (
            db.query(func.count(Notification.id))
            .filter(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .scalar()
            or 0
        )

        items = (
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": math.ceil(total / page_size) if total else 0,
            "unread_count": int(unread_count),
        }

    @staticmethod
    def summary(db: Session, *, user_id: int) -> dict:
        total = (
            db.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id)
            .scalar()
            or 0
        )

        unread = (
            db.query(func.count(Notification.id))
            .filter(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .scalar()
            or 0
        )

        return {
            "total": int(total),
            "unread": int(unread),
            "read": int(total - unread),
        }

    @staticmethod
    def mark_as_read(
        db: Session,
        *,
        user_id: int,
        notification_id: int,
    ) -> Notification:
        notification = (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )

        if notification is None:
            raise LookupError("La notificación no existe.")

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)

            try:
                db.commit()
                db.refresh(notification)
            except Exception:
                db.rollback()
                raise

        return notification

    @staticmethod
    def mark_all_as_read(db: Session, *, user_id: int) -> dict:
        now = datetime.now(timezone.utc)

        notifications = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .all()
        )

        for notification in notifications:
            notification.is_read = True
            notification.read_at = now

        updated = len(notifications)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        return {
            "updated": updated,
            "unread_count": 0,
        }

from __future__ import annotations

import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.models.notification_push_delivery import (
    NotificationPushDelivery,
)
from app.models.user_device import UserDevice
from app.services.firebase_service import FirebaseService


logger = logging.getLogger(__name__)


class PushNotificationService:

    @staticmethod
    def enqueue_for_notification(
        db: Session,
        *,
        notification: Notification,
    ) -> int:
        """
        Crea una entrega pendiente por cada dispositivo FCM
        activo del usuario. No envía nada y no hace commit.
        """

        devices = (
            db.query(UserDevice)
            .filter(
                UserDevice.user_id
                == notification.user_id,
                UserDevice.is_active.is_(True),
                UserDevice.fcm_token.isnot(None),
            )
            .all()
        )

        created = 0

        for device in devices:
            existing = (
                db.query(
                    NotificationPushDelivery
                )
                .filter(
                    NotificationPushDelivery.notification_id
                    == notification.id,
                    NotificationPushDelivery.user_device_id
                    == device.id,
                )
                .first()
            )

            if existing is not None:
                continue

            db.add(
                NotificationPushDelivery(
                    notification_id=
                        notification.id,

                    user_device_id=
                        device.id,

                    status=
                        "PENDING",

                    attempt_count=
                        0,
                )
            )

            created += 1

        return created

    @staticmethod
    def _payload(
        notification: Notification,
    ) -> dict[str, str]:
        return {
            "notification_id":
                str(notification.id),

            "type":
                notification.type or "",

            "event":
                notification.event or "",

            "entity_type":
                notification.entity_type or "",

            "entity_id":
                (
                    str(notification.entity_id)
                    if notification.entity_id
                    is not None
                    else ""
                ),

            "action_url":
                notification.action_url or "",
        }

    @staticmethod
    def process_pending_deliveries(
        db: Session,
        *,
        limit: int | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)

        batch_size = (
            limit
            or settings.push_delivery_batch_size
        )

        deliveries = (
            db.query(NotificationPushDelivery)
            .filter(
                NotificationPushDelivery.status
                == "PENDING",
                or_(
                    NotificationPushDelivery.next_attempt_at
                    .is_(None),
                    NotificationPushDelivery.next_attempt_at
                    <= now,
                ),
            )
            .order_by(
                NotificationPushDelivery.id.asc()
            )
            .limit(batch_size)
            .all()
        )

        result = {
            "processed": 0,
            "sent": 0,
            "retried": 0,
            "failed": 0,
            "cancelled": 0,
        }

        for delivery in deliveries:
            result["processed"] += 1

            try:
                notification = delivery.notification
                device = delivery.user_device

                if (
                    notification is None
                    or device is None
                    or not device.is_active
                    or not device.fcm_token
                ):
                    delivery.status = "CANCELLED"
                    delivery.last_error = (
                        "Dispositivo no disponible."
                    )
                    result["cancelled"] += 1
                    db.commit()
                    continue

                delivery.attempt_count += 1

                push_result = (
                    FirebaseService.send_to_token(
                        token=device.fcm_token,
                        title=notification.title,
                        body=notification.message,
                        data=(
                            PushNotificationService
                            ._payload(notification)
                        ),
                    )
                )

                if push_result["success"]:
                    delivery.status = "SENT"
                    delivery.sent_at = now
                    delivery.firebase_message_id = (
                        push_result["message_id"]
                    )
                    delivery.last_error = None
                    delivery.next_attempt_at = None
                    result["sent"] += 1

                elif push_result["invalid_token"]:
                    # No volvemos a enviar a este token.
                    device.is_active = False

                    delivery.status = "CANCELLED"
                    delivery.last_error = (
                        push_result["error"]
                    )
                    delivery.next_attempt_at = None
                    result["cancelled"] += 1

                elif (
                    delivery.attempt_count
                    >= settings.push_max_retries
                ):
                    delivery.status = "FAILED"
                    delivery.last_error = (
                        push_result["error"]
                    )
                    delivery.next_attempt_at = None
                    result["failed"] += 1

                else:
                    delivery.status = "PENDING"
                    delivery.last_error = (
                        push_result["error"]
                    )

                    delivery.next_attempt_at = (
                        now
                        + timedelta(
                            minutes=(
                                settings
                                .push_retry_delay_minutes
                            )
                        )
                    )

                    result["retried"] += 1

                db.commit()

            except Exception:
                db.rollback()

                logger.exception(
                    "Error procesando push delivery id=%s",
                    delivery.id,
                )

                # La siguiente ejecución volverá a encontrar
                # la entrega si el commit no llegó a ocurrir.

        return result

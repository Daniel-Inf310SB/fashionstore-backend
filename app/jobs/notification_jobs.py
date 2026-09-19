from __future__ import annotations

import logging

from app.database.session import SessionLocal
from app.services.marketing_notification_service import (
    MarketingNotificationService,
)
from app.services.push_notification_service import (
    PushNotificationService,
)


logger = logging.getLogger(__name__)


def run_push_delivery_jobs() -> None:
    db = SessionLocal()

    try:
        result = (
            PushNotificationService
            .process_pending_deliveries(db)
        )

        if result["processed"]:
            logger.info(
                "Push FCM procesados: %s",
                result,
            )

    except Exception:
        db.rollback()
        logger.exception(
            "Error ejecutando job de push FCM."
        )

    finally:
        db.close()


def run_marketing_notification_jobs() -> None:
    db = SessionLocal()

    try:
        result = (
            MarketingNotificationService
            .process_due_campaigns(db)
        )

        if result["processed_campaigns"]:
            logger.info(
                "Campañas de notificación procesadas: %s",
                result,
            )

    except Exception:
        db.rollback()
        logger.exception(
            "Error ejecutando campañas de notificación."
        )

    finally:
        db.close()

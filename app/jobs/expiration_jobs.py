from __future__ import annotations

import logging

from app.database.session import SessionLocal
from app.services.expiration_service import ExpirationService


logger = logging.getLogger(__name__)


def run_expiration_jobs() -> None:
    db = SessionLocal()

    try:
        orders = ExpirationService.expire_due_orders(db)
        reservations = ExpirationService.expire_due_reservations(db)

        if orders["expired"] or orders["reconciled_paid"] or reservations["expired"]:
            logger.info(
                "Expiración automática: orders=%s reservations=%s",
                orders,
                reservations,
            )

    except Exception:
        db.rollback()
        logger.exception("Error ejecutando la expiración automática.")

    finally:
        db.close()

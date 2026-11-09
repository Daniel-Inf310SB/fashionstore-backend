"""Proceso independiente para tareas programadas de FashionStore.

Ejecutar exactamente una instancia: ``python -m app.worker``.
La API ``app.main`` no inicia trabajos automáticos.
"""
from __future__ import annotations

import logging
import signal
import threading
from contextlib import contextmanager
from typing import Iterator

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import settings
from app.database.session import engine
from app.jobs.expiration_jobs import run_expiration_jobs
from app.jobs.notification_jobs import (
    run_marketing_notification_jobs,
    run_push_delivery_jobs,
)
from app.jobs.stripe_reconciliation_jobs import run_stripe_reconciliation_jobs
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

# Identificador fijo para TODOS los despliegues de esta base de datos.
# Un bloqueo de sesión de PostgreSQL permite solo un planificador activo.
WORKER_LOCK_ID = 806_202_611_07
HEALTH_CHECK_SECONDS = 5


def configure_jobs(scheduler: BackgroundScheduler) -> int:
    """Registra las mismas tareas e intervalos anteriormente definidos en main.py."""
    count = 0
    if settings.expiration_scheduler_enabled:
        scheduler.add_job(
            run_expiration_jobs,
            trigger="interval",
            minutes=settings.expiration_check_minutes,
            id="fashionstore-expiration",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        count += 1

    if settings.push_jobs_enabled:
        scheduler.add_job(
            run_push_delivery_jobs,
            trigger="interval",
            seconds=settings.push_job_interval_seconds,
            id="fashionstore-push-delivery",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        count += 1

    if settings.marketing_notification_jobs_enabled:
        scheduler.add_job(
            run_marketing_notification_jobs,
            trigger="interval",
            seconds=settings.marketing_campaign_job_interval_seconds,
            id="fashionstore-marketing-notifications",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        count += 1

    if settings.stripe_reconciliation_enabled and settings.stripe_secret_key:
        scheduler.add_job(
            run_stripe_reconciliation_jobs,
            trigger="interval",
            seconds=max(10, settings.stripe_reconciliation_interval_seconds),
            kwargs={"batch_size": settings.stripe_reconciliation_batch_size},
            id="fashionstore-stripe-reconciliation",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        count += 1
    return count


@contextmanager
def exclusive_worker_connection() -> Iterator[Connection]:
    """Mantiene el advisory lock de sesión durante toda la vida del worker.

    Se utiliza una conexión exclusiva (no se devuelve al pool mientras
    el worker se ejecuta). Nunca se hace un lock transaccional aquí.
    """
    if engine.dialect.name != "postgresql":
        raise RuntimeError("El worker requiere PostgreSQL para garantizar exclusividad")

    with engine.connect() as conn:
        acquired = conn.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": WORKER_LOCK_ID},
        ).scalar_one()
        conn.commit()
        if not acquired:
            raise RuntimeError(
                "Ya existe un worker FashionStore activo para esta base de datos"
            )
        try:
            yield conn
        finally:
            try:
                conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": WORKER_LOCK_ID},
                )
                conn.commit()
            except Exception:
                logger.exception("No se pudo liberar el bloqueo; PostgreSQL lo liberará al cerrar la sesión")


def run() -> None:
    """Ejecuta los trabajos sin abrir un servidor HTTP."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    stop_event = threading.Event()

    def stop_worker(signum: int, _frame: object) -> None:
        logger.info("Señal %s recibida; deteniendo worker", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, stop_worker)
    signal.signal(signal.SIGTERM, stop_worker)

    with exclusive_worker_connection() as lock_conn:
        scheduler = BackgroundScheduler(timezone="UTC")
        count = configure_jobs(scheduler)
        if not count:
            logger.warning("No hay tareas habilitadas. El worker terminará.")
            return

        # Firebase también es necesario aquí: ya no se inicializa desde
        # el mismo proceso que procesa los envíos push.
        FirebaseService.initialize()
        logger.info("Worker exclusivo iniciado con %d tareas", count)
        scheduler.start()
        try:
            while not stop_event.wait(HEALTH_CHECK_SECONDS):
                # Si la conexión se corta, PostgreSQL libera el lock de sesión.
                # Debemos parar inmediatamente para no competir con otro worker.
                lock_conn.execute(text("SELECT 1"))
                lock_conn.commit()
        finally:
            scheduler.shutdown(wait=True)
            logger.info("Worker detenido")


if __name__ == "__main__":
    run()

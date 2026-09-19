from __future__ import annotations

import logging
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings


logger = logging.getLogger(__name__)


class FirebaseService:
    _initialized = False

    @classmethod
    def initialize(cls) -> bool:
        if cls._initialized:
            return True

        if not settings.firebase_enabled:
            logger.info("Firebase está deshabilitado.")
            return False

        credentials_path = settings.firebase_credentials_path

        if not credentials_path:
            logger.warning(
                "FIREBASE_CREDENTIALS_PATH no está configurado."
            )
            return False

        path = Path(credentials_path)

        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            logger.warning(
                "No existe el archivo Firebase: %s",
                path,
            )
            return False

        try:
            if not firebase_admin._apps:
                credential = credentials.Certificate(
                    str(path)
                )

                firebase_admin.initialize_app(
                    credential
                )

            cls._initialized = True

            logger.info(
                "Firebase Admin SDK inicializado correctamente."
            )

            return True

        except Exception:
            logger.exception(
                "No se pudo inicializar Firebase Admin SDK."
            )
            return False

    @classmethod
    def send_to_token(
        cls,
        *,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict:
        """
        Nunca propaga errores de Firebase al flujo comercial.

        Retorna:
        {
            success: bool,
            message_id: str | None,
            invalid_token: bool,
            transient: bool,
            error: str | None
        }
        """

        if not token:
            return {
                "success": False,
                "message_id": None,
                "invalid_token": True,
                "transient": False,
                "error": "FCM token vacío.",
            }

        if not cls.initialize():
            return {
                "success": False,
                "message_id": None,
                "invalid_token": False,
                "transient": True,
                "error": (
                    "Firebase Admin SDK no está disponible."
                ),
            }

        safe_data = {
            str(key): str(value)
            for key, value in (data or {}).items()
        }

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=safe_data,
            token=token,
        )

        try:
            response = messaging.send(
                message
            )

            return {
                "success": True,
                "message_id": response,
                "invalid_token": False,
                "transient": False,
                "error": None,
            }

        except Exception as error:
            error_name = (
                error.__class__.__name__
            )

            error_text = str(error)

            # Clases usadas por Firebase Admin para tokens
            # revocados, inexistentes o incompatibles.
            invalid_names = {
                "UnregisteredError",
                "SenderIdMismatchError",
                "InvalidArgumentError",
            }

            # Errores recuperables: conservamos el token y
            # dejamos que el job reintente más tarde.
            transient_names = {
                "UnavailableError",
                "InternalError",
                "DeadlineExceededError",
                "ResourceExhaustedError",
                "QuotaExceededError",
            }

            invalid_token = (
                error_name in invalid_names
            )

            transient = (
                error_name in transient_names
                or not invalid_token
            )

            logger.warning(
                "FCM error (%s): %s",
                error_name,
                error_text,
            )

            return {
                "success": False,
                "message_id": None,
                "invalid_token": invalid_token,
                "transient": transient,
                "error": (
                    f"{error_name}: {error_text}"
                )[:2000],
            }

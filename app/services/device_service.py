from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user_device import UserDevice
from app.schemas.device import DeviceRegisterRequest


class DeviceService:

    @staticmethod
    def register_or_refresh(
        db: Session,
        *,
        user_id: int,
        payload: DeviceRegisterRequest,
    ) -> UserDevice:
        """
        Vincula el token FCM con el usuario autenticado.

        Si Firebase rota el token, reutiliza el registro del
        mismo device_id. Si el token ya pertenecía a otro
        usuario/dispositivo, se transfiere al usuario actual
        para evitar enviar notificaciones privadas al usuario
        anterior.
        """

        token_owner = (
            db.query(UserDevice)
            .filter(
                UserDevice.fcm_token
                == payload.fcm_token
            )
            .first()
        )

        same_device = (
            db.query(UserDevice)
            .filter(
                UserDevice.user_id == user_id,
                UserDevice.device_id
                == payload.device_id,
            )
            .first()
        )

        if (
            token_owner is not None
            and same_device is not None
            and token_owner.id != same_device.id
        ):
            # El token actual manda: eliminamos el registro
            # duplicado del mismo dispositivo del usuario.
            db.delete(same_device)
            db.flush()
            device = token_owner

        elif token_owner is not None:
            device = token_owner

        elif same_device is not None:
            device = same_device

        else:
            device = UserDevice(
                user_id=user_id,
                device_id=payload.device_id,
                platform=payload.platform.strip().lower(),
                fcm_token=payload.fcm_token,
            )

            db.add(device)

        device.user_id = user_id
        device.device_id = payload.device_id
        device.device_name = (
            payload.device_name.strip()
            if payload.device_name
            else None
        )
        device.platform = (
            payload.platform.strip().lower()
        )
        device.fcm_token = payload.fcm_token
        device.app_version = (
            payload.app_version.strip()
            if payload.app_version
            else None
        )
        device.is_active = True
        device.last_seen_at = (
            datetime.now(timezone.utc)
        )

        try:
            db.commit()
            db.refresh(device)

        except Exception:
            db.rollback()
            raise

        return device

    @staticmethod
    def list_my_devices(
        db: Session,
        *,
        user_id: int,
    ) -> dict:
        items = (
            db.query(UserDevice)
            .filter(
                UserDevice.user_id == user_id
            )
            .order_by(
                UserDevice.updated_at.desc(),
                UserDevice.id.desc(),
            )
            .all()
        )

        return {
            "items": items,
            "total": len(items),
        }

    @staticmethod
    def deactivate(
        db: Session,
        *,
        user_id: int,
        device_id: str,
    ) -> None:
        device = (
            db.query(UserDevice)
            .filter(
                UserDevice.user_id == user_id,
                UserDevice.device_id
                == device_id,
            )
            .first()
        )

        if device is None:
            # Idempotente para logout.
            return

        device.is_active = False
        device.last_seen_at = (
            datetime.now(timezone.utc)
        )

        try:
            db.commit()

        except Exception:
            db.rollback()
            raise

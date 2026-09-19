from fastapi import (
    APIRouter,
    Depends,
    Path,
    status,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.permissions import (
    require_authenticated_user,
)
from app.models.user import User
from app.models.notification_push_delivery import NotificationPushDelivery
from app.schemas.device import (
    DeviceDeactivateResponse,
    DeviceListResponse,
    DevicePushTestResponse,
    DeviceRegisterRequest,
    DeviceResponse,
)
from app.services.device_service import DeviceService
from app.services.notification_service import NotificationService


router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
)


@router.post(
    "/register",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
)
def register_device(
    payload: DeviceRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    return DeviceService.register_or_refresh(
        db,
        user_id=current_user.id,
        payload=payload,
    )


@router.get(
    "",
    response_model=DeviceListResponse,
)
def list_my_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    return DeviceService.list_my_devices(
        db,
        user_id=current_user.id,
    )




@router.post(
    "/test-push",
    response_model=DevicePushTestResponse,
)
def create_test_push(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    """
    Crea una notificación interna de prueba para el usuario
    autenticado. El job FCM la enviará a sus dispositivos activos.
    """
    notification = NotificationService.create(
        db,
        user_id=current_user.id,
        notification_type="SYSTEM",
        event="PUSH_TEST",
        title="FashionStore",
        message="Las notificaciones push están funcionando correctamente.",
        entity_type="SYSTEM",
        entity_id=None,
        action_url=None,
        dedupe_key=None,
    )

    queued_deliveries = (
        db.query(NotificationPushDelivery)
        .filter(
            NotificationPushDelivery.notification_id
            == notification.id
        )
        .count()
    )

    db.commit()
    db.refresh(notification)

    return DevicePushTestResponse(
        notification_id=notification.id,
        queued_deliveries=queued_deliveries,
        message=(
            "Notificación de prueba creada. "
            "El job FCM procesará las entregas pendientes."
        ),
    )


@router.delete(
    "/{device_id}",
    response_model=DeviceDeactivateResponse,
)
def deactivate_device(
    device_id: str = Path(
        ...,
        min_length=1,
        max_length=255,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    DeviceService.deactivate(
        db,
        user_id=current_user.id,
        device_id=device_id,
    )

    return DeviceDeactivateResponse(
        message=(
            "Dispositivo desactivado correctamente."
        )
    )

from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.reservations import (
    require_reservations_customer,
    require_reservations_manage,
    require_reservations_staff_manage,
    require_reservations_view,
)

from app.models.user import User

from app.schemas.reservation import (
    CustomerReservationCountResponse,
    CustomerReservationCreate,
    ReservationCancel,
    ReservationCreate,
    ReservationListResponse,
    ReservationResponse,
    ReservationStatusUpdate,
)

from app.services.reservation_service import (
    ReservationService,
)


router = APIRouter(
    prefix="/reservations",

    tags=[
        "Reservations",
    ],
)


# =========================================================
# MANEJO DE ERRORES
# =========================================================

def handle_reservation_error(
    error: Exception,
) -> None:

    if isinstance(
        error,
        PermissionError,
    ):

        raise HTTPException(
            status_code=
                status.HTTP_403_FORBIDDEN,

            detail=
                str(
                    error
                ),
        ) from error


    if isinstance(
        error,
        LookupError,
    ):

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                str(
                    error
                ),
        ) from error


    if isinstance(
        error,
        ValueError,
    ):

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                str(
                    error
                ),
        ) from error


    raise error


# =========================================================
# CU28 - LISTAR RESERVAS
# =========================================================

@router.get(
    "",

    response_model=
        ReservationListResponse,
)
def list_reservations(

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
    ),

    search: str | None = Query(
        default=None,
        max_length=100,
    ),

    reservation_status: Literal[
        "PENDING",
        "CONFIRMED",
        "PREPARING",
        "READY",
        "ATTENDED",
        "COMPLETED",
        "CANCELLED",
        "EXPIRED",
    ] | None = Query(
        default=None,
        alias="status",
    ),

    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),

    customer_id: int | None = Query(
        default=None,
        ge=1,
    ),

    db: Session = Depends(
        get_db,
    ),

    current_user: User = Depends(
        require_reservations_view,
    ),
):

    try:

        return (
            ReservationService
            .list_reservations(
                db=db,

                current_user=
                    current_user,

                page=
                    page,

                page_size=
                    page_size,

                search=
                    search,

                reservation_status=
                    reservation_status,

                branch_id=
                    branch_id,

                customer_id=
                    customer_id,
            )
        )

    except Exception as error:

        handle_reservation_error(
            error
        )


# =========================================================
# CU28 - CONTADOR DE MIS RESERVAS (CLIENTE)
#
# Global a todas las sucursales del cliente. El frontend
# puede usar total_active como badge en el header.
# =========================================================

@router.get(
    "/mine/count",
    response_model=CustomerReservationCountResponse,
)
def count_my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reservations_customer),
):

    try:
        return ReservationService.get_my_reservation_count(
            db=db,
            current_user=current_user,
        )
    except Exception as error:
        handle_reservation_error(error)


# =========================================================
# CU28 - MIS RESERVAS (CLIENTE)
#
# Por defecto lista todas las sucursales. branch_id es solo
# un filtro opcional y cambiar de sucursal NO oculta ni
# modifica reservas existentes.
# =========================================================

@router.get(
    "/mine",
    response_model=ReservationListResponse,
)
def list_my_reservations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    reservation_status: Literal[
        "PENDING",
        "CONFIRMED",
        "PREPARING",
        "READY",
        "ATTENDED",
        "COMPLETED",
        "CANCELLED",
        "EXPIRED",
    ] | None = Query(default=None, alias="status"),
    branch_id: int | None = Query(default=None, ge=1),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reservations_customer),
):

    try:
        return ReservationService.list_reservations(
            db=db,
            current_user=current_user,
            page=page,
            page_size=page_size,
            search=search,
            reservation_status=reservation_status,
            branch_id=branch_id,
            active_only=active_only,
        )
    except Exception as error:
        handle_reservation_error(error)


# =========================================================
# CU28 - CREAR MI RESERVA (CLIENTE)
#
# customer_id se obtiene del usuario autenticado.
# =========================================================

@router.post(
    "/mine",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_my_reservation(
    data: CustomerReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reservations_customer),
):

    try:
        create_data = ReservationCreate(
            customer_id=current_user.id,
            branch_id=data.branch_id,
            notes=data.notes,
            items=data.items,
        )

        return ReservationService.create_reservation(
            db=db,
            data=create_data,
            current_user=current_user,
        )
    except Exception as error:
        handle_reservation_error(error)


# =========================================================
# CU28 - CONSULTAR MI RESERVA (CLIENTE)
# =========================================================

@router.get(
    "/mine/{reservation_id}",
    response_model=ReservationResponse,
)
def get_my_reservation(
    reservation_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reservations_customer),
):

    try:
        return ReservationService.get_reservation(
            db=db,
            reservation_id=reservation_id,
            current_user=current_user,
        )
    except Exception as error:
        handle_reservation_error(error)


# =========================================================
# CU28 - CANCELAR MI RESERVA (CLIENTE)
# =========================================================

@router.patch(
    "/mine/{reservation_id}/cancel",
    response_model=ReservationResponse,
)
def cancel_my_reservation(
    data: ReservationCancel,
    reservation_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reservations_customer),
):

    try:
        return ReservationService.cancel_reservation(
            db=db,
            reservation_id=reservation_id,
            current_user=current_user,
            reason=data.reason,
        )
    except Exception as error:
        handle_reservation_error(error)


# =========================================================
# CU28 - CREAR RESERVA
# =========================================================

@router.post(
    "",

    response_model=
        ReservationResponse,

    status_code=
        status.HTTP_201_CREATED,
)
def create_reservation(

    data: ReservationCreate,

    db: Session = Depends(
        get_db,
    ),

    current_user: User = Depends(
        require_reservations_manage,
    ),
):

    try:

        return (
            ReservationService
            .create_reservation(
                db=db,

                data=
                    data,

                current_user=
                    current_user,
            )
        )

    except Exception as error:

        handle_reservation_error(
            error
        )


# =========================================================
# CU28 - CONSULTAR RESERVA
# =========================================================

@router.get(
    "/{reservation_id}",

    response_model=
        ReservationResponse,
)
def get_reservation(

    reservation_id: int = Path(
        ...,
        ge=1,
    ),

    db: Session = Depends(
        get_db,
    ),

    current_user: User = Depends(
        require_reservations_manage,
    ),
):

    try:

        return (
            ReservationService
            .get_reservation(
                db=db,

                reservation_id=
                    reservation_id,

                current_user=
                    current_user,
            )
        )

    except Exception as error:

        handle_reservation_error(
            error
        )


# =========================================================
# CU29 - VINCULAR PRENDAS RESERVADAS
#
# PENDING item
#       ↓
# RESERVED item
#
# reserved_quantity += quantity
# movimiento RESERVE
# auditoría
# =========================================================

@router.patch(
    "/{reservation_id}/items/link",

    response_model=
        ReservationResponse,
)
def link_reserved_items(

    reservation_id: int = Path(
        ...,
        ge=1,
    ),

    db: Session = Depends(
        get_db,
    ),

    current_user: User = Depends(
        require_reservations_staff_manage,
    ),
):

    try:

        return (
            ReservationService
            .link_reserved_items(
                db=db,

                reservation_id=
                    reservation_id,

                current_user=
                    current_user,
            )
        )

    except Exception as error:

        handle_reservation_error(
            error
        )


# =========================================================
# CU28 - CONFIRMAR RESERVA
# =========================================================

@router.patch(
    "/{reservation_id}/confirm",

    response_model=
        ReservationResponse,
)
def confirm_reservation(

    reservation_id: int = Path(
        ...,
        ge=1,
    ),

    db: Session = Depends(
        get_db,
    ),

    current_user: User = Depends(
        require_reservations_staff_manage,
    ),
):

    try:

        return (
            ReservationService
            .confirm_reservation(
                db=db,

                reservation_id=
                    reservation_id,

                current_user=
                    current_user,
            )
        )

    except Exception as error:

        handle_reservation_error(
            error
        )


# =========================================================
# CU30 / CU31 - CAMBIAR ESTADO OPERATIVO
#
# CONFIRMED
#    ↓
# PREPARING
#    ↓
# READY
#    ↓
# ATTENDED
#    ↓
# COMPLETED
#
# Las transiciones válidas se controlan
# dentro de ReservationService.
# =========================================================

@router.patch(
    "/{reservation_id}/status",

    response_model=
        ReservationResponse,
)
def update_reservation_status(

    data: ReservationStatusUpdate,

    reservation_id: int = Path(
        ...,
        ge=1,
    ),

    db: Session = Depends(
        get_db,
    ),

    current_user: User = Depends(
        require_reservations_staff_manage,
    ),
):

    try:

        return (
            ReservationService
            .update_operational_status(
                db=db,

                reservation_id=
                    reservation_id,

                new_status=
                    data.status,

                current_user=
                    current_user,
            )
        )

    except Exception as error:

        handle_reservation_error(
            error
        )


# =========================================================
# CU28 / CU29 - CANCELAR RESERVA
# =========================================================

@router.patch(
    "/{reservation_id}/cancel",

    response_model=
        ReservationResponse,
)
def cancel_reservation(

    data: ReservationCancel,

    reservation_id: int = Path(
        ...,
        ge=1,
    ),

    db: Session = Depends(
        get_db,
    ),

    current_user: User = Depends(
        require_reservations_manage,
    ),
):

    try:

        return (
            ReservationService
            .cancel_reservation(
                db=db,

                reservation_id=
                    reservation_id,

                current_user=
                    current_user,

                reason=
                    data.reason,
            )
        )

    except Exception as error:

        handle_reservation_error(
            error
        )
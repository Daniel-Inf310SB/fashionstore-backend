from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# ESTADOS DE RESERVA
# =========================================================

ReservationStatus = Literal[
    "PENDING",
    "CONFIRMED",
    "PREPARING",
    "READY",
    "ATTENDED",
    "COMPLETED",
    "CANCELLED",
    "EXPIRED",
]


OperationalReservationStatus = Literal[
    "PREPARING",
    "READY",
    "ATTENDED",
    "COMPLETED",
]


# =========================================================
# CU28 - RESUMEN DE CLIENTE
# =========================================================

class ReservationCustomerResponse(BaseModel):

    id: int

    first_name: str

    last_name: str | None = None

    email: str

    phone: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU28 - RESUMEN DE SUCURSAL
# =========================================================

class ReservationBranchResponse(BaseModel):

    id: int

    name: str

    address: str

    phone: str | None = None

    city_id: int

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU28 - PRODUCTO
# =========================================================

class ReservationProductResponse(BaseModel):

    id: int

    code: str

    name: str

    brand: str | None = None

    cover_image_url: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU28 - TALLA
# =========================================================

class ReservationSizeResponse(BaseModel):

    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU28 - COLOR
# =========================================================

class ReservationColorResponse(BaseModel):

    id: int

    name: str

    hex_code: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU28 - VARIANTE
# =========================================================

class ReservationVariantResponse(BaseModel):

    id: int

    sku: str

    product_id: int

    size_id: int

    color_id: int

    image_url: str | None = None

    product: ReservationProductResponse

    size: ReservationSizeResponse

    color: ReservationColorResponse

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU28 - PRENDA SOLICITADA
# =========================================================

class ReservationItemCreate(BaseModel):

    product_variant_id: int = Field(
        ...,
        ge=1,
    )

    quantity: int = Field(
        ...,
        ge=1,
        le=100,
    )


# =========================================================
# CU28 - CREAR RESERVA
# =========================================================

class ReservationCreate(BaseModel):

    customer_id: int | None = Field(
        default=None,
        ge=1,
    )

    branch_id: int = Field(
        ...,
        ge=1,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    # expires_at no se recibe al crear. El backend lo asigna al
    # confirmar la reserva, cuando empieza el plazo de retiro.

    items: list[
        ReservationItemCreate
    ] = Field(
        ...,
        min_length=1,
        max_length=50,
    )


# =========================================================
# CU28 - CREAR MI RESERVA (CLIENTE)
#
# El cliente nunca envía customer_id. El backend lo toma
# del JWT/sesión autenticada. Tampoco controla expires_at.
# =========================================================

class CustomerReservationCreate(BaseModel):

    branch_id: int = Field(
        ...,
        ge=1,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    items: list[
        ReservationItemCreate
    ] = Field(
        ...,
        min_length=1,
        max_length=50,
    )


# =========================================================
# CU28 - AGREGAR PRODUCTOS A MI RESERVA PENDING
# =========================================================

class ReservationAddItems(BaseModel):

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    items: list[
        ReservationItemCreate
    ] = Field(
        ...,
        min_length=1,
        max_length=50,
    )


# =========================================================
# CU28 - CANCELAR RESERVA
# =========================================================

class ReservationCancel(BaseModel):

    reason: str | None = Field(
        default=None,
        max_length=255,
    )


# =========================================================
# CU30 / CU31 - CAMBIAR ESTADO OPERATIVO
# =========================================================

class ReservationStatusUpdate(BaseModel):

    status: OperationalReservationStatus


# =========================================================
# CU28 - PRENDA RESERVADA
# =========================================================

class ReservationItemResponse(BaseModel):

    id: int

    reservation_id: int

    product_variant_id: int

    quantity: int

    unit_price: Decimal

    subtotal: Decimal

    status: str

    created_at: datetime

    product_variant: ReservationVariantResponse

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU28 - RESERVA
# =========================================================

class ReservationResponse(BaseModel):

    id: int

    reservation_code: str

    customer_id: int

    branch_id: int

    status: ReservationStatus

    notes: str | None = None

    expires_at: datetime | None = None

    prepared_at: datetime | None = None

    attended_at: datetime | None = None

    completed_at: datetime | None = None

    cancelled_at: datetime | None = None

    created_at: datetime

    updated_at: datetime

    # Campos derivados para simplificar el frontend cliente.
    is_active: bool

    can_cancel: bool

    total_items: int

    total_units: int

    total_amount: Decimal

    customer: ReservationCustomerResponse

    branch: ReservationBranchResponse

    items: list[
        ReservationItemResponse
    ]

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CU28 - LISTA DE RESERVAS
# =========================================================

class ReservationListResponse(BaseModel):

    items: list[
        ReservationResponse
    ]

    page: int

    page_size: int

    total: int

    total_pages: int


# =========================================================
# CU28 - CONTADOR / RESUMEN DE MIS RESERVAS
# =========================================================

class CustomerReservationCountResponse(BaseModel):

    total_all: int

    total_active: int

    pending: int

    confirmed: int

    preparing: int

    ready: int

    attended: int

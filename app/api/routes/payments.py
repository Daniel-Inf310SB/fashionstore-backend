from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.payments import (
    require_payments_manage,
    require_payments_view,
)
from app.models.user import User
from app.schemas.payment import (
    PaymentCancelRequest,
    PaymentListResponse,
    PaymentResponse,
    PaymentStatusResponse,
)
from app.services.payment_service import PaymentService


router = APIRouter(
    prefix="/payments",
    tags=["Electronic Payments"],
)


# =========================================================
# MANEJO DE ERRORES
# =========================================================

def handle_payment_error(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

    if isinstance(error, LookupError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    if isinstance(error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    raise error


# =========================================================
# CU38 / CU39 - LISTAR PAGOS ELECTRÓNICOS PARA ADMIN
# =========================================================

@router.get(
    "",
    response_model=PaymentListResponse,
)
def list_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None, max_length=150),
    branch_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    order_id: int | None = Query(default=None, ge=1),
    sale_id: int | None = Query(default=None, ge=1),
    source_type: Literal["ORDER", "SALE"] | None = Query(default=None),
    payment_status: Literal[
        "PENDING",
        "PROCESSING",
        "APPROVED",
        "REJECTED",
        "FAILED",
        "CANCELLED",
        "REFUNDED",
    ] | None = Query(default=None, alias="status"),
    payment_method: Literal[
        "CARD",
        "QR",
        "TRANSFER",
    ] | None = Query(default=None),
    channel: Literal[
        "ONLINE",
        "CASH_DESK",
    ] | None = Query(default=None),
    provider: str | None = Query(default=None, max_length=100),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    min_amount: Decimal | None = Query(default=None, ge=0),
    max_amount: Decimal | None = Query(default=None, ge=0),
    sort_by: Literal[
        "created_at",
        "updated_at",
        "amount",
        "payment_code",
        "status",
        "payment_method",
    ] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_payments_view),
):
    if (
        min_amount is not None
        and max_amount is not None
        and min_amount > max_amount
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_amount no puede ser mayor que max_amount.",
        )

    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from no puede ser posterior a date_to.",
        )

    try:
        return PaymentService.list_payments(
            db=db,
            current_user=current_user,
            page=page,
            page_size=page_size,
            search=search,
            branch_id=branch_id,
            customer_id=customer_id,
            order_id=order_id,
            sale_id=sale_id,
            source_type=source_type,
            payment_status=payment_status,
            payment_method=payment_method,
            channel=channel,
            provider=provider,
            date_from=date_from,
            date_to=date_to,
            min_amount=min_amount,
            max_amount=max_amount,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as error:
        handle_payment_error(error)


# =========================================================
# CU39 - CONSULTAR ESTADO DE PAGO
# Debe ir antes de /{payment_id} para mantener rutas claras.
# =========================================================

@router.get(
    "/{payment_id}/status",
    response_model=PaymentStatusResponse,
)
def get_payment_status(
    payment_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_payments_view),
):
    try:
        return PaymentService.get_payment_status(
            db=db,
            current_user=current_user,
            payment_id=payment_id,
        )
    except Exception as error:
        handle_payment_error(error)


# =========================================================
# CU38 - CANCELAR INTENTO PENDIENTE
# No permite aprobar/rechazar manualmente pagos.
# =========================================================

@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
)
def cancel_payment(
    data: PaymentCancelRequest,
    payment_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_payments_manage),
):
    try:
        return PaymentService.cancel_payment(
            db=db,
            current_user=current_user,
            payment_id=payment_id,
            reason=data.reason,
        )
    except Exception as error:
        handle_payment_error(error)


# =========================================================
# CU38 / CU39 - DETALLE DEL PAGO
# =========================================================

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(
    payment_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_payments_view),
):
    try:
        return PaymentService.get_payment(
            db=db,
            current_user=current_user,
            payment_id=payment_id,
        )
    except Exception as error:
        handle_payment_error(error)

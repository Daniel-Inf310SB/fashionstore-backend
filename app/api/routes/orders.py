from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.orders import (
    require_purchases_create,
    require_purchases_manage,
    require_purchases_view,
)
from app.models.user import User
from app.schemas.order import (
    CheckoutPreviewResponse,
    OrderCreate,
    OrderListResponse,
    OrderManagementSummaryResponse,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.expiration_service import ExpirationService
from app.services.order_service import OrderService


router = APIRouter(prefix="/orders", tags=["Digital Purchases"])


def handle_order_error(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=403, detail=str(error)) from error
    if isinstance(error, LookupError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise error


# CU33 - El checkout recalcula precios y stock en backend; no confía en Angular.
@router.get("/checkout/{cart_id}", response_model=CheckoutPreviewResponse)
def checkout_preview(
    cart_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_purchases_create),
):
    try:
        return OrderService.checkout_preview(
            db=db, current_user=current_user, cart_id=cart_id
        )
    except Exception as error:
        handle_order_error(error)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_purchases_create),
):
    try:
        return OrderService.create_order(db=db, current_user=current_user, data=data)
    except Exception as error:
        handle_order_error(error)


@router.get("", response_model=OrderListResponse)
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None, max_length=120),
    order_status: Literal[
        "PENDING_PAYMENT", "PAYMENT_FAILED", "PAID", "PREPARING", "READY_FOR_PICKUP",
        "SHIPPED", "DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED",
    ] | None = Query(default=None, alias="status"),
    branch_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    payment_status: Literal[
        "PENDING", "PROCESSING", "APPROVED", "REJECTED",
        "FAILED", "CANCELLED", "REFUNDED",
    ] | None = Query(default=None),
    payment_method: Literal["CASH", "CARD", "QR", "TRANSFER"] | None = Query(default=None),
    delivery_type: Literal["PICKUP", "DELIVERY"] | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    min_total: Decimal | None = Query(default=None, ge=0),
    max_total: Decimal | None = Query(default=None, ge=0),
    sort_by: Literal[
        "created_at", "updated_at", "total_amount", "order_code", "status",
    ] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_purchases_view),
):
    if min_total is not None and max_total is not None and min_total > max_total:
        raise HTTPException(status_code=400, detail="min_total no puede ser mayor que max_total.")
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from no puede ser posterior a date_to.")
    try:
        ExpirationService.expire_due_orders(db)
        return OrderService.list_orders(
            db=db,
            current_user=current_user,
            page=page,
            page_size=page_size,
            search=search,
            order_status=order_status,
            branch_id=branch_id,
            customer_id=customer_id,
            payment_status=payment_status,
            payment_method=payment_method,
            delivery_type=delivery_type,
            date_from=date_from,
            date_to=date_to,
            min_total=min_total,
            max_total=max_total,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as error:
        handle_order_error(error)


@router.get(
    "/management/summary",
    response_model=OrderManagementSummaryResponse,
)
def management_summary(
    branch_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_purchases_manage),
):
    try:
        ExpirationService.expire_due_orders(db)
        return OrderService.management_summary(
            db=db,
            current_user=current_user,
            branch_id=branch_id,
        )
    except Exception as error:
        handle_order_error(error)


@router.get("/mine", response_model=OrderListResponse)
def list_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    order_status: Literal[
        "PENDING_PAYMENT", "PAYMENT_FAILED", "PAID", "PREPARING", "READY_FOR_PICKUP",
        "SHIPPED", "DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED",
    ] | None = Query(default=None, alias="status"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_purchases_view),
):
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from no puede ser posterior a date_to.")

    try:
        ExpirationService.expire_due_orders(db)
        return OrderService.list_my_orders(
            db=db,
            current_user=current_user,
            page=page,
            page_size=page_size,
            order_status=order_status,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as error:
        handle_order_error(error)


# Debe estar antes de /{order_id}.
@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    data: OrderStatusUpdate,
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_purchases_manage),
):
    try:
        return OrderService.update_order_status(
            db=db,
            current_user=current_user,
            order_id=order_id,
            new_status=data.status,
            note=data.note,
            tracking_code=data.tracking_code,
        )
    except Exception as error:
        handle_order_error(error)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_purchases_view),
):
    try:
        # La comprobación de expiración es defensiva. Si una orden histórica
        # tiene una inconsistencia de reserva, no impedimos consultar su
        # detalle: el scheduler/servicio la registrará como omitida.
        try:
            ExpirationService.expire_order_if_needed(
                db,
                order_id=order_id,
            )
        except Exception as expiration_error:
            db.rollback()
            print(
                f"[EXPIRATION][ORDER] No se pudo expirar {order_id}: "
                f"{expiration_error}"
            )

        return OrderService.get_order(
            db=db, current_user=current_user, order_id=order_id
        )
    except Exception as error:
        handle_order_error(error)

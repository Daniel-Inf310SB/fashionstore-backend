
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.permissions import require_authenticated_user
from app.models.user import User
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationResponse,
    NotificationSummaryResponse,
)
from app.services.notification_service import NotificationService


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get("", response_model=NotificationListResponse)
def list_my_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_read: bool | None = Query(default=None),
    notification_type: Literal[
        "ORDER",
        "RESERVATION",
        "PAYMENT",
        "SYSTEM",
    ] | None = Query(default=None, alias="type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return NotificationService.list_my_notifications(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        is_read=is_read,
        notification_type=notification_type,
    )


@router.get("/summary", response_model=NotificationSummaryResponse)
def notification_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return NotificationService.summary(
        db,
        user_id=current_user.id,
    )


@router.patch("/read-all", response_model=MarkAllReadResponse)
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return NotificationService.mark_all_as_read(
        db,
        user_id=current_user.id,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    try:
        return NotificationService.mark_as_read(
            db,
            user_id=current_user.id,
            notification_id=notification_id,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

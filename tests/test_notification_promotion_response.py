"""Regresión: notificaciones de campañas no deben provocar ResponseValidationError."""
from datetime import datetime, timezone

import pytest

from app.schemas.notification import NotificationListResponse, NotificationResponse


@pytest.mark.parametrize("notification_type", [
    "ORDER", "RESERVATION", "PAYMENT", "SYSTEM",
    "PROMOTION", "COLLECTION", "SEASON",
])
def test_notification_response_accepts_supported_types(notification_type):
    item = NotificationResponse.model_validate({
        "id": 1,
        "user_id": 2,
        "type": notification_type,
        "event": "PROMOTION_LAUNCHED",
        "title": "Nueva promoción",
        "message": "Descubre las ofertas",
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    })
    page = NotificationListResponse(
        items=[item], page=1, page_size=50, total=1,
        total_pages=1, unread_count=1,
    )
    assert page.items[0].type == notification_type

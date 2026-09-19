from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


NotificationType = Literal["ORDER", "RESERVATION", "PAYMENT", "SYSTEM"]


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: NotificationType
    event: str
    title: str
    message: str
    entity_type: str | None = None
    entity_id: int | None = None
    action_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
    unread_count: int


class NotificationSummaryResponse(BaseModel):
    total: int
    unread: int
    read: int


class MarkAllReadResponse(BaseModel):
    updated: int
    unread_count: int

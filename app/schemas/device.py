from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(
        min_length=1,
        max_length=255,
    )

    fcm_token: str = Field(
        min_length=10,
        max_length=500,
    )

    platform: str = Field(
        min_length=2,
        max_length=30,
    )

    device_name: str | None = Field(
        default=None,
        max_length=150,
    )

    app_version: str | None = Field(
        default=None,
        max_length=50,
    )


class DeviceResponse(BaseModel):
    id: int
    device_id: str | None
    device_name: str | None
    platform: str
    app_version: str | None
    is_active: bool
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class DeviceListResponse(BaseModel):
    items: list[DeviceResponse]
    total: int


class DeviceDeactivateResponse(BaseModel):
    message: str


class DevicePushTestResponse(BaseModel):
    notification_id: int
    queued_deliveries: int
    message: str

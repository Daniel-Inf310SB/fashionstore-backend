from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class ReturnLineIn(BaseModel):
    order_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

class ReturnCreate(BaseModel):
    order_id: int = Field(gt=0)
    reason: str = Field(min_length=8, max_length=500)
    items: list[ReturnLineIn] = Field(min_length=1)

class ReturnDecision(BaseModel):
    note: str | None = Field(default=None, max_length=500)

class ReturnLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_item_id: int
    quantity: int

class ReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    order_id: int
    customer_id: int
    status: str
    reason: str
    admin_note: str | None
    reviewed_by: int | None
    received_by: int | None
    created_at: datetime
    reviewed_at: datetime | None
    received_at: datetime | None
    items: list[ReturnLineOut]


class ReturnEligibleLine(BaseModel):
    order_item_id: int
    product_variant_id: int
    purchased_quantity: int
    already_requested_quantity: int
    available_quantity: int
    unit_price: Decimal
    subtotal: Decimal


class ReturnEligibilityOut(BaseModel):
    order_id: int
    order_code: str
    order_status: str
    can_request: bool
    reason: str | None
    delivered_at: datetime | None = None
    return_deadline: datetime | None = None
    return_window_days: int = 7
    items: list[ReturnEligibleLine]

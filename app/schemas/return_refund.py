from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class RefundPreview(BaseModel):
    return_request_id: int
    payment_id: int
    currency: str
    amount: Decimal
    status: str
    note: str

class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    return_request_id: int
    tenant_id: int
    payment_id: int
    requested_by: int
    amount: Decimal
    currency: str
    status: str
    stripe_refund_id: str | None
    failure_reason: str | None
    created_at: datetime

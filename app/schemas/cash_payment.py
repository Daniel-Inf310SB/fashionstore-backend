from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field

CashDeskPaymentMethod = Literal['CASH','CARD','QR','TRANSFER']

class CashDeskPaymentCreate(BaseModel):
    payment_method: CashDeskPaymentMethod
    amount_received: Decimal | None = Field(default=None, gt=0)
    provider: str | None = Field(default=None, max_length=100)
    external_transaction_id: str | None = Field(default=None, max_length=150)
    external_reference: str | None = Field(default=None, max_length=150)

class CashDeskPaymentResponse(BaseModel):
    id: int
    payment_code: str
    sale_id: int
    user_id: int | None = None
    payment_method: CashDeskPaymentMethod
    channel: Literal['CASH_DESK']
    provider: str | None = None
    amount: Decimal
    amount_received: Decimal | None = None
    change_amount: Decimal
    currency: str
    status: Literal['APPROVED']
    external_transaction_id: str | None = None
    external_reference: str | None = None
    paid_at: datetime
    created_at: datetime

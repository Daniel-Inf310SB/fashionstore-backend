from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PaymentMethod = Literal["CARD", "QR", "TRANSFER"]
PaymentStatus = Literal[
    "PENDING", "PROCESSING", "APPROVED", "REJECTED",
    "FAILED", "CANCELLED", "REFUNDED",
]
PaymentChannel = Literal["ONLINE", "CASH_DESK"]
PaymentSourceType = Literal["ORDER", "SALE"]


class PaymentCustomerResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    email: str
    phone: str | None = None
    document_number: str | None = None
    model_config = ConfigDict(from_attributes=True)


class PaymentBranchResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str | None = None
    city_id: int
    model_config = ConfigDict(from_attributes=True)


class PaymentOrderResponse(BaseModel):
    id: int
    order_code: str
    status: str
    customer_id: int
    branch_id: int
    total_amount: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentSaleResponse(BaseModel):
    id: int
    sale_code: str
    status: str
    branch_id: int
    cashier_id: int
    customer_id: int | None = None
    total_amount: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentResponse(BaseModel):
    id: int
    payment_code: str
    order_id: int | None = None
    sale_id: int | None = None
    user_id: int | None = None
    source_type: PaymentSourceType
    source_code: str
    payment_method: PaymentMethod
    channel: PaymentChannel
    provider: str | None = None
    amount: Decimal
    currency: str
    status: PaymentStatus
    external_transaction_id: str | None = None
    external_reference: str | None = None
    failure_reason: str | None = None
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    customer: PaymentCustomerResponse | None = None
    branch: PaymentBranchResponse
    order: PaymentOrderResponse | None = None
    sale: PaymentSaleResponse | None = None


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class PaymentStatusResponse(BaseModel):
    id: int
    payment_code: str
    source_type: PaymentSourceType
    source_code: str
    status: PaymentStatus
    payment_method: PaymentMethod
    amount: Decimal
    currency: str
    provider: str | None = None
    external_transaction_id: str | None = None
    failure_reason: str | None = None
    paid_at: datetime | None = None
    updated_at: datetime


class PaymentCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class StripePaymentCreate(BaseModel):
    order_id: int = Field(..., ge=1)


class StripePaymentIntentResponse(BaseModel):
    payment: PaymentResponse
    client_secret: str
    publishable_key: str


class PaymentMethodResponse(BaseModel):
    code: str
    name: str
    provider: str
    enabled: bool
    description: str | None = None


class PaymentMethodsResponse(BaseModel):
    items: list[PaymentMethodResponse]

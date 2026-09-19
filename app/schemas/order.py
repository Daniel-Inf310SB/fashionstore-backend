from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


OrderStatus = Literal[
    "PENDING_PAYMENT",
    "PAYMENT_FAILED",
    "PAID",
    "PREPARING",
    "READY_FOR_PICKUP",
    "SHIPPED",
    "DELIVERED",
    "COMPLETED",
    "CANCELLED",
    "REFUNDED",
]

PaymentMethod = Literal["CASH", "CARD", "QR", "TRANSFER"]
PaymentStatus = Literal[
    "PENDING", "PROCESSING", "APPROVED", "REJECTED",
    "FAILED", "CANCELLED", "REFUNDED",
]


class OrderCreate(BaseModel):
    cart_id: int = Field(..., ge=1)
    delivery_type: Literal["PICKUP", "DELIVERY"] = "PICKUP"
    shipping_address: str | None = Field(default=None, max_length=500)


class OrderStatusUpdate(BaseModel):
    status: Literal[
        "PREPARING", "READY_FOR_PICKUP", "SHIPPED", "DELIVERED",
        "COMPLETED", "CANCELLED",
    ]
    note: str | None = Field(default=None, max_length=500)
    tracking_code: str | None = Field(default=None, max_length=120)


class CheckoutItemResponse(BaseModel):
    product_variant_id: int
    sku: str
    product_name: str
    size: str
    color: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class CheckoutPreviewResponse(BaseModel):
    cart_id: int
    branch_id: int
    branch_name: str
    items: list[CheckoutItemResponse]
    total_items: int
    total_units: int
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    currency: str = "BOB"


class OrderCustomerResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    email: str
    phone: str | None = None
    document_number: str | None = None
    model_config = ConfigDict(from_attributes=True)


class OrderBranchResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str | None = None
    city_id: int
    model_config = ConfigDict(from_attributes=True)


class OrderProductResponse(BaseModel):
    id: int
    code: str
    name: str
    brand: str | None = None
    cover_image_url: str | None = None
    model_config = ConfigDict(from_attributes=True)


class OrderSizeResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class OrderColorResponse(BaseModel):
    id: int
    name: str
    hex_code: str | None = None
    model_config = ConfigDict(from_attributes=True)


class OrderVariantResponse(BaseModel):
    id: int
    sku: str
    product_id: int
    size_id: int
    color_id: int
    image_url: str | None = None
    product: OrderProductResponse
    size: OrderSizeResponse
    color: OrderColorResponse
    model_config = ConfigDict(from_attributes=True)


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_variant_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    created_at: datetime
    product_variant: OrderVariantResponse
    model_config = ConfigDict(from_attributes=True)


class OrderPaymentResponse(BaseModel):
    id: int
    payment_code: str
    payment_method: PaymentMethod
    channel: str
    provider: str | None = None
    amount: Decimal
    currency: str
    status: PaymentStatus
    external_transaction_id: str | None = None
    paid_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OrderReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    receipt_type: str
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    payment_method: str
    currency: str
    pdf_url: str | None = None
    email_status: str
    issued_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    order_code: str
    customer_id: int
    branch_id: int
    status: OrderStatus
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    delivery_type: Literal["PICKUP", "DELIVERY"]
    shipping_address: str | None = None
    tracking_code: str | None = None
    paid_at: datetime | None = None
    ready_for_pickup_at: datetime | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    payment_expires_at: datetime
    created_at: datetime
    updated_at: datetime
    total_items: int
    total_units: int
    customer: OrderCustomerResponse
    branch: OrderBranchResponse
    items: list[OrderItemResponse]
    payments: list[OrderPaymentResponse] = Field(default_factory=list)
    receipt: OrderReceiptResponse | None = None
    allowed_transitions: list[OrderStatus] = Field(default_factory=list)


class OrderStatusCount(BaseModel):
    status: OrderStatus
    count: int


class OrderManagementSummaryResponse(BaseModel):
    branch_id: int | None = None
    branch_name: str | None = None
    total_orders: int
    total_revenue: Decimal
    attention_count: int
    pickup_ready_count: int
    delivery_in_progress_count: int
    status_counts: list[OrderStatusCount] = Field(default_factory=list)


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    page: int
    page_size: int
    total: int
    total_pages: int

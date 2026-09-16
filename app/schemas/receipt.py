from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class ReceiptItemResponse(BaseModel):
    id: int
    receipt_id: int
    product_name: str
    sku: str
    size_name: str | None = None
    color_name: str | None = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    receipt_type: str
    order_id: int | None = None
    sale_id: int | None = None
    customer_name: str
    customer_email: str | None = None
    customer_document: str | None = None
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    payment_method: str
    currency: str
    pdf_url: str | None = None
    email_status: str
    emailed_at: datetime | None = None
    issued_at: datetime
    created_at: datetime
    items: list[ReceiptItemResponse] = Field(default_factory=list)

from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

SaleStatus = Literal['PENDING','PAID','CANCELLED','REFUNDED']

class SaleItemCreate(BaseModel):
    product_variant_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)

class SaleCreate(BaseModel):
    branch_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    items: list[SaleItemCreate] = Field(..., min_length=1)

class SaleProductResponse(BaseModel):
    id: int
    code: str
    name: str
    brand: str | None = None
    cover_image_url: str | None = None
    model_config = ConfigDict(from_attributes=True)

class SaleSizeResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class SaleColorResponse(BaseModel):
    id: int
    name: str
    hex_code: str | None = None
    model_config = ConfigDict(from_attributes=True)

class SaleVariantResponse(BaseModel):
    id: int
    sku: str
    product_id: int
    size_id: int
    color_id: int
    image_url: str | None = None
    product: SaleProductResponse
    size: SaleSizeResponse
    color: SaleColorResponse
    model_config = ConfigDict(from_attributes=True)

class SaleItemResponse(BaseModel):
    id: int
    sale_id: int
    product_variant_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    created_at: datetime
    product_variant: SaleVariantResponse
    model_config = ConfigDict(from_attributes=True)

class SaleUserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    email: str
    document_number: str | None = None
    model_config = ConfigDict(from_attributes=True)

class SaleBranchResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str | None = None
    city_id: int
    model_config = ConfigDict(from_attributes=True)

class SalePaymentSummary(BaseModel):
    id: int
    payment_code: str
    payment_method: str
    channel: str
    amount: Decimal
    currency: str
    status: str
    paid_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SaleReceiptSummary(BaseModel):
    id: int
    receipt_number: str
    receipt_type: str
    total_amount: Decimal
    payment_method: str
    currency: str
    issued_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SaleResponse(BaseModel):
    id: int
    sale_code: str
    branch_id: int
    cashier_id: int
    customer_id: int | None = None
    status: SaleStatus
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    total_items: int
    total_units: int
    branch: SaleBranchResponse
    cashier: SaleUserResponse
    customer: SaleUserResponse | None = None
    items: list[SaleItemResponse]
    payments: list[SalePaymentSummary] = Field(default_factory=list)
    receipt: SaleReceiptSummary | None = None

class SaleListResponse(BaseModel):
    items: list[SaleResponse]
    page: int
    page_size: int
    total: int
    total_pages: int

# =========================================================
# CONTEXTO POS DEL CAJERO
# =========================================================

class CashierContextBranchResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str | None = None
    city_id: int
    model_config = ConfigDict(from_attributes=True)


class CashierSaleContextResponse(BaseModel):
    cashier: SaleUserResponse
    branch: CashierContextBranchResponse


# =========================================================
# CATÁLOGO POS
# =========================================================

class PosCatalogItemResponse(BaseModel):
    inventory_id: int
    product_variant_id: int
    product_id: int
    product_code: str
    product_name: str
    brand: str | None = None
    sku: str
    size_name: str
    color_name: str
    color_hex_code: str | None = None
    image_url: str | None = None
    available_quantity: int
    unit_price: Decimal


class PosCatalogListResponse(BaseModel):
    items: list[PosCatalogItemResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


# =========================================================
# CLIENTES DISPONIBLES PARA VENTA
# =========================================================

class SaleCustomerSearchItem(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    email: str
    phone: str | None = None
    document_number: str | None = None


class SaleCustomerSearchResponse(BaseModel):
    items: list[SaleCustomerSearchItem]
    page: int
    page_size: int
    total: int
    total_pages: int


from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class PostSaleItemIn(BaseModel):
    source_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class PostSaleCreate(BaseModel):
    source_channel: Literal["ONLINE", "POS"]
    source_id: int = Field(gt=0)
    resolution_type: Literal["REFUND", "EXCHANGE"]
    reason: str = Field(min_length=8, max_length=500)
    items: list[PostSaleItemIn] = Field(min_length=1, max_length=50)
    idempotency_key: UUID = Field(default_factory=uuid4)


class PostSaleDecision(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=1000)


class PostSaleInspectionLine(BaseModel):
    case_item_id: int = Field(gt=0)
    condition: Literal["RESELLABLE", "DAMAGED", "QUARANTINE"]
    note: str | None = Field(default=None, max_length=500)


class PostSaleInspection(BaseModel):
    items: list[PostSaleInspectionLine] = Field(min_length=1, max_length=50)


class PostSaleReplacementLine(BaseModel):
    product_variant_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class PostSaleQuote(BaseModel):
    items: list[PostSaleReplacementLine] = Field(min_length=1, max_length=50)


class PostSaleSettlementIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal["CASH", "CARD", "QR", "TRANSFER"] | None = None
    mode: Literal["DEMO_LOCAL", "EXTERNAL_MANUAL", "STRIPE_TEST"] | None = None
    reference: str | None = Field(default=None, max_length=150)


class PostSaleCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=500)

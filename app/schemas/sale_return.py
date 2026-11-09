from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field

class SaleReturnLineIn(BaseModel):
    sale_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

class SaleReturnCreate(BaseModel):
    sale_id: int = Field(gt=0)
    reason: str = Field(min_length=8, max_length=500)
    items: list[SaleReturnLineIn] = Field(min_length=1, max_length=50)

class SaleReturnDecision(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)

class SaleReturnInspectionLine(BaseModel):
    sale_item_id: int = Field(gt=0)
    condition: Literal['RESELLABLE','DAMAGED']

class SaleReturnInspection(BaseModel):
    items: list[SaleReturnInspectionLine] = Field(min_length=1, max_length=50)

class SaleReturnRefund(BaseModel):
    mode: Literal['DEMO', 'EXTERNAL_MANUAL']
    reference: str | None = Field(default=None, max_length=150)

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class InspectionDecision(BaseModel):
    decision: Literal['RESTOCK', 'DAMAGED']
    note: str = Field(min_length=8, max_length=500)


class InspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    return_item_id: int
    tenant_id: int
    inspector_id: int
    decision: str
    note: str
    movement_id: int | None
    created_at: datetime


class InspectionLineOut(BaseModel):
    return_item_id: int
    order_item_id: int
    product_variant_id: int
    branch_id: int
    quantity: int
    decision: str
    movement_id: int | None

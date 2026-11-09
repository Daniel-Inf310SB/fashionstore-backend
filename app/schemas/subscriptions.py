from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class PlanCreate(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    monthly_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="BOB", pattern=r"^[A-Z]{3}$")
    max_branches: int | None = Field(default=None, ge=1)
    max_staff: int | None = Field(default=None, ge=1)
    features: list[str] = Field(default_factory=list)
    is_active: bool = True

class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    monthly_price: Decimal | None = Field(default=None, ge=0)
    max_branches: int | None = Field(default=None, ge=1)
    max_staff: int | None = Field(default=None, ge=1)
    features: list[str] | None = None
    is_active: bool | None = None

class PlanOut(PlanCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

class SubscriptionAssign(BaseModel):
    plan_id: int
    status: Literal["ACTIVE", "SUSPENDED", "CANCELLED"] = "ACTIVE"
    expires_at: datetime | None = None

class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    plan_id: int
    status: str
    starts_at: datetime
    expires_at: datetime | None
    pending_plan_id: int | None = None
    duration_months: int | None = None
    price_snapshot: Decimal | None = None
    currency_snapshot: str | None = None

class EntitlementOut(BaseModel):
    tenant_id: int
    subscription_status: str | None
    plan_code: str | None
    max_branches: int | None
    max_staff: int | None
    features: list[str]
    allowed: bool

class PaymentRequest(BaseModel):
    plan_id: int = Field(ge=1)
    duration_months: Literal[1, 3, 6, 12]
    method: Literal["CASH", "QR", "TRANSFER", "MANUAL"]
    reference: str = Field(min_length=4, max_length=100)

class SubscriptionPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subscription_id: int
    plan_id: int
    duration_months: int
    amount: Decimal
    currency: str
    method: str
    status: str
    reference: str
    paid_at: datetime | None
    period_starts_at: datetime | None
    period_expires_at: datetime | None
    created_at: datetime

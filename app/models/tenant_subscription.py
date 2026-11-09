from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_subscription_current"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pending_plan_id: Mapped[int | None] = mapped_column(ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency_snapshot: Mapped[str | None] = mapped_column(String(3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

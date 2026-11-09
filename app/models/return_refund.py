from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, String, Numeric, DateTime, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class ReturnRefund(Base):
    __tablename__ = "return_refunds"
    __table_args__ = (
        UniqueConstraint("return_request_id", name="uq_refund_return_request"),
        UniqueConstraint("idempotency_key", name="uq_refund_idempotency"),
        UniqueConstraint("stripe_refund_id", name="uq_refund_stripe_id"),
        CheckConstraint("amount > 0", name="ck_return_refund_positive"),
        CheckConstraint("status IN ('PREPARED','PROCESSING','SUCCEEDED','FAILED','MANUAL_REVIEW')",name="ck_return_refund_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    return_request_id: Mapped[int] = mapped_column(ForeignKey("return_requests.id", ondelete="RESTRICT"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PREPARED")
    stripe_refund_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

"""Receipt of an idempotent offline cart addition, committed with the cart change."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class CartOfflineOperation(Base):
    __tablename__ = "cart_offline_operations"
    __table_args__ = (
        Index("uq_cart_offline_customer_operation", "customer_id", "client_operation_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    client_operation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    product_variant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

from datetime import datetime
from sqlalchemy import ForeignKey, String, Integer, DateTime, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class ReturnRequest(Base):
    __tablename__ = "return_requests"
    __table_args__ = (CheckConstraint("status IN ('REQUESTED','APPROVED','REJECTED','RECEIVED','CANCELLED')", name="ck_return_status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="REQUESTED")
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    admin_note: Mapped[str | None] = mapped_column(String(500))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items = relationship("ReturnItem", back_populates="request", cascade="all, delete-orphan", lazy="selectin")

class ReturnItem(Base):
    __tablename__ = "return_items"
    __table_args__ = (UniqueConstraint("return_request_id", "order_item_id", name="uq_return_order_item"), CheckConstraint("quantity > 0", name="ck_return_quantity_positive"))
    id: Mapped[int] = mapped_column(primary_key=True)
    return_request_id: Mapped[int] = mapped_column(ForeignKey("return_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    request = relationship("ReturnRequest", back_populates="items")

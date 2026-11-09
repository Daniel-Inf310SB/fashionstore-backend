from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String,
    Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PostSaleCase(Base):
    """Unified after-sales case for online orders and in-store sales."""
    __tablename__ = "post_sale_cases"
    __table_args__ = (
        CheckConstraint(
            "(source_channel = 'ONLINE' AND order_id IS NOT NULL AND sale_id IS NULL) OR "
            "(source_channel = 'POS' AND sale_id IS NOT NULL AND order_id IS NULL)",
            name="ck_post_sale_case_single_source",
        ),
        CheckConstraint(
            "source_channel IN ('ONLINE','POS')",
            name="ck_post_sale_case_channel",
        ),
        CheckConstraint(
            "resolution_type IN ('REFUND','EXCHANGE')",
            name="ck_post_sale_case_resolution",
        ),
        CheckConstraint(
            "status IN ('REQUESTED','APPROVED','REJECTED','RECEIVED','INSPECTED','AWAITING_SETTLEMENT','COMPLETED','CANCELLED')",
            name="ck_post_sale_case_status",
        ),
        CheckConstraint(
            "original_amount >= 0 AND replacement_amount >= 0 AND difference_amount >= 0 AND settlement_amount >= 0",
            name="ck_post_sale_case_amounts",
        ),
        UniqueConstraint("case_code", name="uq_post_sale_case_code"),
        UniqueConstraint("idempotency_key", name="uq_post_sale_case_idempotency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_code: Mapped[str] = mapped_column(String(60), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(36), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_channel: Mapped[str] = mapped_column(String(10), nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True, index=True)
    sale_id: Mapped[int | None] = mapped_column(ForeignKey("sales.id", ondelete="RESTRICT"), nullable=True, index=True)
    resolution_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(28), nullable=False, default="REQUESTED", server_default="REQUESTED", index=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    staff_note: Mapped[str | None] = mapped_column(String(1000))
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    replacement_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    difference_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    settlement_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="NONE", server_default="NONE")
    settlement_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    settlement_status: Mapped[str] = mapped_column(String(16), nullable=False, default="NOT_REQUIRED", server_default="NOT_REQUIRED")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    inspected_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["PostSaleCaseItem"]] = relationship(
        "PostSaleCaseItem", cascade="all, delete-orphan", lazy="selectin", back_populates="case"
    )
    replacement_items: Mapped[list["PostSaleReplacementItem"]] = relationship(
        "PostSaleReplacementItem", cascade="all, delete-orphan", lazy="selectin", back_populates="case"
    )
    events: Mapped[list["PostSaleCaseEvent"]] = relationship(
        "PostSaleCaseEvent", cascade="all, delete-orphan", lazy="selectin", back_populates="case",
        order_by="PostSaleCaseEvent.created_at"
    )
    settlement: Mapped["PostSaleSettlement | None"] = relationship(
        "PostSaleSettlement", cascade="all, delete-orphan", uselist=False, lazy="selectin", back_populates="case"
    )


class PostSaleCaseItem(Base):
    __tablename__ = "post_sale_case_items"
    __table_args__ = (
        CheckConstraint(
            "(order_item_id IS NOT NULL AND sale_item_id IS NULL) OR "
            "(sale_item_id IS NOT NULL AND order_item_id IS NULL)",
            name="ck_post_sale_case_item_single_source",
        ),
        CheckConstraint("quantity > 0 AND original_unit_paid >= 0 AND original_total >= 0", name="ck_post_sale_case_item_amounts"),
        CheckConstraint("condition IS NULL OR condition IN ('RESELLABLE','DAMAGED','QUARANTINE')", name="ck_post_sale_case_item_condition"),
        UniqueConstraint("case_id", "order_item_id", name="uq_post_sale_case_order_item"),
        UniqueConstraint("case_id", "sale_item_id", name="uq_post_sale_case_sale_item"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("post_sale_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=True)
    sale_item_id: Mapped[int | None] = mapped_column(ForeignKey("sale_items.id", ondelete="RESTRICT"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    original_unit_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    original_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    condition: Mapped[str | None] = mapped_column(String(16))
    inspection_note: Mapped[str | None] = mapped_column(String(500))
    inventory_movement_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_movements.id", ondelete="RESTRICT"), nullable=True, unique=True)
    case: Mapped["PostSaleCase"] = relationship("PostSaleCase", back_populates="items")


class PostSaleReplacementItem(Base):
    __tablename__ = "post_sale_replacement_items"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_price >= 0 AND subtotal >= 0", name="ck_post_sale_replacement_amounts"),
        UniqueConstraint("case_id", "product_variant_id", name="uq_post_sale_replacement_variant"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("post_sale_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    product_variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    inventory_movement_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_movements.id", ondelete="RESTRICT"), nullable=True, unique=True)
    case: Mapped["PostSaleCase"] = relationship("PostSaleCase", back_populates="replacement_items")
    variant = relationship("ProductVariant", lazy="selectin")


class PostSaleCaseEvent(Base):
    __tablename__ = "post_sale_case_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("post_sale_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(28))
    to_status: Mapped[str | None] = mapped_column(String(28))
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    case: Mapped["PostSaleCase"] = relationship("PostSaleCase", back_populates="events")


class PostSaleSettlement(Base):
    __tablename__ = "post_sale_settlements"
    __table_args__ = (
        CheckConstraint("kind IN ('COLLECT','REFUND')", name="ck_post_sale_settlement_kind"),
        CheckConstraint("amount > 0", name="ck_post_sale_settlement_amount"),
        CheckConstraint("status IN ('PROCESSING','COMPLETED','FAILED','MANUAL_REVIEW')", name="ck_post_sale_settlement_status"),
        CheckConstraint("method IS NULL OR method IN ('CASH','CARD','QR','TRANSFER')", name="ck_post_sale_settlement_method"),
        CheckConstraint("mode IS NULL OR mode IN ('BRANCH_COLLECTION','DEMO_LOCAL','EXTERNAL_MANUAL','STRIPE_TEST')", name="ck_post_sale_settlement_mode"),
        UniqueConstraint("case_id", name="uq_post_sale_settlement_case"),
        UniqueConstraint("idempotency_key", name="uq_post_sale_settlement_idempotency"),
        UniqueConstraint("stripe_refund_id", name="uq_post_sale_settlement_stripe_refund"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("post_sale_cases.id", ondelete="RESTRICT"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BOB", server_default="BOB")
    method: Mapped[str | None] = mapped_column(String(20))
    mode: Mapped[str | None] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(150))
    stripe_refund_id: Mapped[str | None] = mapped_column(String(150))
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    case: Mapped["PostSaleCase"] = relationship("PostSaleCase", back_populates="settlement")

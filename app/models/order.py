from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            """
            status IN (
                'PENDING_PAYMENT',
                'PAYMENT_FAILED',
                'PAID',
                'PREPARING',
                'READY_FOR_PICKUP',
                'SHIPPED',
                'DELIVERED',
                'COMPLETED',
                'CANCELLED',
                'REFUNDED'
            )
            """,
            name="ck_order_status",
        ),
        CheckConstraint(
            "delivery_type IN ('PICKUP', 'DELIVERY')",
            name="ck_order_delivery_type",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_order_subtotal_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_order_discount_nonnegative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_order_total_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    order_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING_PAYMENT",
        server_default="PENDING_PAYMENT",
        index=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    delivery_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PICKUP",
        server_default="PICKUP",
    )

    shipping_address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    tracking_code: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ready_for_pickup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    shipped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    customer = relationship(
        "User",
        back_populates="orders",
        foreign_keys=[customer_id],
    )

    branch = relationship(
        "Branch",
        back_populates="orders",
    )

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="order",
        foreign_keys="Payment.order_id",
    )

    receipt: Mapped["Receipt | None"] = relationship(
        "Receipt",
        back_populates="order",
        uselist=False,
        foreign_keys="Receipt.order_id",
    )
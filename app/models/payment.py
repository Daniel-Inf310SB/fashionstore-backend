from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            """
            (
                order_id IS NOT NULL
                AND sale_id IS NULL
            )
            OR
            (
                order_id IS NULL
                AND sale_id IS NOT NULL
            )
            """,
            name="ck_payment_single_source",
        ),
        CheckConstraint(
            """
            payment_method IN (
                'CASH',
                'CARD',
                'QR',
                'TRANSFER'
            )
            """,
            name="ck_payment_method",
        ),
        CheckConstraint(
            "channel IN ('ONLINE', 'CASH_DESK')",
            name="ck_payment_channel",
        ),
        CheckConstraint(
            """
            status IN (
                'PENDING',
                'PROCESSING',
                'APPROVED',
                'REJECTED',
                'FAILED',
                'CANCELLED',
                'REFUNDED'
            )
            """,
            name="ck_payment_status",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_payment_amount_positive",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    payment_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    payment_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="BOB",
        server_default="BOB",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )

    external_transaction_id: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    external_reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
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

    order: Mapped["Order | None"] = relationship(
        "Order",
        back_populates="payments",
        foreign_keys=[order_id],
    )

    sale: Mapped["Sale | None"] = relationship(
        "Sale",
        back_populates="payments",
        foreign_keys=[sale_id],
    )

    user = relationship(
        "User",
        back_populates="payments",
        foreign_keys=[user_id],
    )
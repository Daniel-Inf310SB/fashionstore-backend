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


class Receipt(Base):
    __tablename__ = "receipts"

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
            name="ck_receipt_single_source",
        ),
        CheckConstraint(
            "receipt_type IN ('ONLINE_PURCHASE', 'IN_STORE_SALE')",
            name="ck_receipt_type",
        ),
        CheckConstraint(
            """
            email_status IN (
                'NOT_REQUESTED',
                'PENDING',
                'SENT',
                'FAILED'
            )
            """,
            name="ck_receipt_email_status",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_receipt_subtotal_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_receipt_discount_nonnegative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_receipt_total_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    receipt_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    receipt_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
        index=True,
    )

    sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
        index=True,
    )

    customer_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    customer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    customer_document: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
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
    )

    payment_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="BOB",
        server_default="BOB",
    )

    pdf_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    email_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NOT_REQUESTED",
        server_default="NOT_REQUESTED",
        index=True,
    )

    emailed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order: Mapped["Order | None"] = relationship(
        "Order",
        back_populates="receipt",
        foreign_keys=[order_id],
    )

    sale: Mapped["Sale | None"] = relationship(
        "Sale",
        back_populates="receipt",
        foreign_keys=[sale_id],
    )

    items: Mapped[list["ReceiptItem"]] = relationship(
        "ReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )
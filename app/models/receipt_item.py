from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_receipt_item_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_receipt_item_unit_price_nonnegative",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_receipt_item_subtotal_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    receipt_id: Mapped[int] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    size_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    color_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    receipt: Mapped["Receipt"] = relationship(
        "Receipt",
        back_populates="items",
    )
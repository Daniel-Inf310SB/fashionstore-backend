from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SaleItem(Base):
    __tablename__ = "sale_items"

    __table_args__ = (
        UniqueConstraint(
            "sale_id",
            "product_variant_id",
            name="uq_sale_item_variant",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_sale_item_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_sale_item_price_nonnegative",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_sale_item_subtotal_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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

    sale: Mapped["Sale"] = relationship(
        "Sale",
        back_populates="items",
    )

    product_variant = relationship(
        "ProductVariant",
        back_populates="sale_items",
    )
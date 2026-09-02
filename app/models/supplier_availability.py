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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SupplierAvailability(Base):
    __tablename__ = "supplier_availabilities"

    __table_args__ = (
        UniqueConstraint(
            "supplier_product_id",
            "product_variant_id",
            name="uq_supplier_product_variant_availability",
        ),
        CheckConstraint(
            "available_quantity >= 0",
            name="ck_supplier_availability_quantity_nonnegative",
        ),
        CheckConstraint(
            "status IN ('AVAILABLE', 'LOW_STOCK', 'OUT_OF_STOCK')",
            name="ck_supplier_availability_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    supplier_product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "supplier_products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    available_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="AVAILABLE",
        server_default="AVAILABLE",
        index=True,
    )

    purchase_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    last_checked_at: Mapped[datetime] = mapped_column(
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    supplier_product: Mapped["SupplierProduct"] = relationship(
        "SupplierProduct",
        back_populates="availabilities",
    )

    product_variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant",
    )

    def __repr__(self) -> str:
        return (
            f"<SupplierAvailability("
            f"id={self.id}, "
            f"supplier_product_id={self.supplier_product_id}, "
            f"product_variant_id={self.product_variant_id}, "
            f"available_quantity={self.available_quantity}"
            f")>"
        )

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "product_id",
            name="uq_supplier_product",
        ),
        UniqueConstraint(
            "supplier_id",
            "supplier_code",
            name="uq_supplier_supplier_code",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            "suppliers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    supplier_code: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    minimum_order_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    lead_time_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="supplier_products",
    )

    product: Mapped["Product"] = relationship(
        "Product",
    )

    availabilities: Mapped[list["SupplierAvailability"]] = relationship(
        "SupplierAvailability",
        back_populates="supplier_product",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<SupplierProduct("
            f"id={self.id}, "
            f"supplier_id={self.supplier_id}, "
            f"product_id={self.product_id}"
            f")>"
        )

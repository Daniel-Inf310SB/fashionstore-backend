from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Inventory(Base):
    """
    Existencia actual de una variante de producto en una sucursal.

    Una fila representa exactamente:
        Sucursal + ProductVariant (producto + talla + color)

    No existe una tabla separada para inventario global:
    el inventario global se obtiene sumando/agrupando estas filas.
    """

    __tablename__ = "inventories"

    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "product_variant_id",
            name="uq_inventory_branch_product_variant",
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_inventory_stock_quantity_nonnegative",
        ),
        CheckConstraint(
            "reserved_quantity >= 0",
            name="ck_inventory_reserved_quantity_nonnegative",
        ),
        CheckConstraint(
            "reserved_quantity <= stock_quantity",
            name="ck_inventory_reserved_not_greater_than_stock",
        ),
        CheckConstraint(
            "minimum_stock >= 0",
            name="ck_inventory_minimum_stock_nonnegative",
        ),
        CheckConstraint(
            "maximum_stock IS NULL OR maximum_stock >= minimum_stock",
            name="ck_inventory_maximum_stock_valid",
        ),
        CheckConstraint(
            "reorder_point >= 0",
            name="ck_inventory_reorder_point_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # Cantidad física actualmente existente en la sucursal.
    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # Parte del stock físico que está comprometida por reservas.
    reserved_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # Parámetros administrativos para control de inventario.
    minimum_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    maximum_stock: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    reorder_point: Mapped[int] = mapped_column(
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

    # No se necesitan imports directos de Branch/ProductVariant:
    # SQLAlchemy resuelve las relaciones por nombre.
    branch: Mapped["Branch"] = relationship(
        "Branch",
    )

    product_variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant",
    )

    # Los movimientos son historial/auditoría.
    # No usamos delete-orphan para evitar borrarlos accidentalmente.
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="inventory",
        order_by="InventoryMovement.created_at",
    )

    @property
    def available_quantity(self) -> int:
        """
        Stock realmente disponible para vender o reservar.
        """
        return self.stock_quantity - self.reserved_quantity

    @property
    def is_low_stock(self) -> bool:
        """
        Indica si la cantidad disponible alcanzó el punto de reposición.
        """
        return self.available_quantity <= self.reorder_point

    def __repr__(self) -> str:
        return (
            f"<Inventory("
            f"id={self.id}, "
            f"branch_id={self.branch_id}, "
            f"product_variant_id={self.product_variant_id}, "
            f"stock_quantity={self.stock_quantity}, "
            f"reserved_quantity={self.reserved_quantity}"
            f")>"
        )

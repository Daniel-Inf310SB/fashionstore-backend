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
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class InventoryMovement(Base):
    """
    Historial auditable de todos los cambios del inventario.

    quantity siempre es positiva.
    El efecto del movimiento se determina con movement_type.

    Ejemplos:
      ENTRY          -> aumenta stock físico
      SALE           -> disminuye stock físico
      RESERVE        -> aumenta reserved_quantity
      RELEASE        -> disminuye reserved_quantity
      ADJUSTMENT_IN  -> aumenta stock
      ADJUSTMENT_OUT -> disminuye stock
    """

    __tablename__ = "inventory_movements"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_inventory_movement_quantity_positive",
        ),
        CheckConstraint(
            """
            movement_type IN (
                'ENTRY',
                'SALE',
                'ADJUSTMENT_IN',
                'ADJUSTMENT_OUT',
                'RETURN_IN',
                'RETURN_OUT',
                'RESERVE',
                'RELEASE',
                'TRANSFER_IN',
                'TRANSFER_OUT'
            )
            """,
            name="ck_inventory_movement_type",
        ),
        CheckConstraint(
            "stock_before >= 0",
            name="ck_inventory_movement_stock_before_nonnegative",
        ),
        CheckConstraint(
            "stock_after >= 0",
            name="ck_inventory_movement_stock_after_nonnegative",
        ),
        CheckConstraint(
            "reserved_before >= 0",
            name="ck_inventory_movement_reserved_before_nonnegative",
        ),
        CheckConstraint(
            "reserved_after >= 0",
            name="ck_inventory_movement_reserved_after_nonnegative",
        ),
        CheckConstraint(
            "reserved_before <= stock_before",
            name="ck_inventory_movement_reserved_before_valid",
        ),
        CheckConstraint(
            "reserved_after <= stock_after",
            name="ck_inventory_movement_reserved_after_valid",
        ),
        CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name="ck_inventory_movement_unit_cost_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    inventory_id: Mapped[int] = mapped_column(
        ForeignKey(
            "inventories.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    movement_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    # Siempre positiva. La dirección la define movement_type.
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Snapshot antes/después para trazabilidad.
    stock_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stock_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reserved_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    reserved_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # Origen de una entrada o devolución a proveedor.
    # Es nullable porque ventas, reservas y ajustes no siempre
    # tienen un proveedor asociado.
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "suppliers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # Usuario/empleado que registró o provocó el movimiento.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # Costo histórico por unidad al momento del movimiento.
    # Es útil para entradas de proveedor y evita depender del
    # precio actual de SupplierProduct.
    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    # Referencia genérica para conectar el movimiento más adelante
    # con venta, reserva, devolución, transferencia, etc.
    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    reference_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    # Código externo/opcional: factura, orden de compra, comprobante, etc.
    reference_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    inventory: Mapped["Inventory"] = relationship(
        "Inventory",
        back_populates="movements",
    )

    supplier: Mapped["Supplier | None"] = relationship(
        "Supplier",
    )

    user: Mapped["User | None"] = relationship(
        "User",
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryMovement("
            f"id={self.id}, "
            f"inventory_id={self.inventory_id}, "
            f"movement_type={self.movement_type!r}, "
            f"quantity={self.quantity}, "
            f"stock_before={self.stock_before}, "
            f"stock_after={self.stock_after}"
            f")>"
        )

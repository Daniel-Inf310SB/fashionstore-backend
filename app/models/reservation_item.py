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
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class ReservationItem(Base):
    __tablename__ = "reservation_items"

    __table_args__ = (
        UniqueConstraint(
            "reservation_id",
            "product_variant_id",
            name="uq_reservation_item_variant",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_reservation_item_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_reservation_item_unit_price_nonnegative",
        ),
        CheckConstraint(
            """
            status IN (
                'PENDING',
                'RESERVED',
                'RELEASED',
                'CONSUMED'
            )
            """,
            name="ck_reservation_item_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    reservation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "reservations.id",
            ondelete="CASCADE",
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

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # =====================================================
    # ESTADO CU29
    #
    # PENDING:
    # Solicitud registrada, aún no apartada físicamente.
    #
    # RESERVED:
    # Encargado confirmó el apartado físico.
    #
    # RELEASED:
    # Prenda liberada por cancelación o vencimiento.
    #
    # CONSUMED:
    # Prenda utilizada definitivamente por una operación
    # posterior (venta / atención).
    # =====================================================

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    reservation: Mapped["Reservation"] = relationship(
        "Reservation",
        back_populates="items",
    )

    product_variant = relationship(
        "ProductVariant",
        back_populates="reservation_items",
    )
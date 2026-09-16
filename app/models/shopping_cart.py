from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class ShoppingCart(Base):
    __tablename__ = "shopping_carts"

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'CONVERTED', 'ABANDONED')",
            name="ck_shopping_cart_status",
        ),
        # Un cliente puede conservar muchos carritos históricos,
        # pero solo uno ACTIVE por sucursal.
        Index(
            "uq_shopping_cart_active_customer_branch",
            "customer_id",
            "branch_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =====================================================
    # CU32 - SUCURSAL DEL CARRITO
    #
    # Es nullable para no romper carritos antiguos.
    # Los nuevos carritos deberían guardar la sucursal
    # seleccionada por el cliente.
    # =====================================================

    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
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

    customer = relationship(
        "User",
        back_populates="shopping_carts",
        foreign_keys=[customer_id],
    )

    branch = relationship(
        "Branch",
        foreign_keys=[branch_id],
    )

    items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )

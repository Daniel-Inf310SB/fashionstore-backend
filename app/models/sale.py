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


class Sale(Base):
    __tablename__ = "sales"

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PAID', 'CANCELLED', 'REFUNDED')",
            name="ck_sale_status",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_sale_subtotal_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_sale_discount_nonnegative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_sale_total_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    sale_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    cashier_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
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
        default=0,
        server_default="0",
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

    branch = relationship(
        "Branch",
        back_populates="sales",
    )

    cashier = relationship(
        "User",
        back_populates="sales_as_cashier",
        foreign_keys=[cashier_id],
    )

    customer = relationship(
        "User",
        back_populates="sales_as_customer",
        foreign_keys=[customer_id],
    )

    items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="sale",
        foreign_keys="Payment.sale_id",
    )

    receipt: Mapped["Receipt | None"] = relationship(
        "Receipt",
        back_populates="sale",
        uselist=False,
        foreign_keys="Receipt.sale_id",
    )
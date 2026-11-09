"""Devoluciones de ventas presenciales, independientes de pedidos online."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class SaleReturn(Base):
    __tablename__ = 'sale_returns'
    __table_args__ = (
        CheckConstraint("status IN ('REQUESTED','APPROVED','REJECTED','RECEIVED','INSPECTED','REFUNDED','CANCELLED')", name='ck_sale_return_status'),
        CheckConstraint('requested_amount >= 0', name='ck_sale_return_amount'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='RESTRICT'), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey('branches.id', ondelete='RESTRICT'), nullable=False, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey('sales.id', ondelete='RESTRICT'), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='REQUESTED')
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    staff_note: Mapped[str | None] = mapped_column(String(500))
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    received_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    inspected_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    refunded_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    refund_mode: Mapped[str | None] = mapped_column(String(24))  # DEMO / EXTERNAL_MANUAL
    refund_reference: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items: Mapped[list['SaleReturnItem']] = relationship('SaleReturnItem', cascade='all, delete-orphan', lazy='selectin', back_populates='request')

class SaleReturnItem(Base):
    __tablename__ = 'sale_return_items'
    __table_args__ = (UniqueConstraint('sale_return_id', 'sale_item_id', name='uq_sale_return_item'), CheckConstraint('quantity > 0', name='ck_sale_return_item_qty'))
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_return_id: Mapped[int] = mapped_column(ForeignKey('sale_returns.id', ondelete='CASCADE'), nullable=False, index=True)
    sale_item_id: Mapped[int] = mapped_column(ForeignKey('sale_items.id', ondelete='RESTRICT'), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    condition: Mapped[str | None] = mapped_column(String(16))
    request: Mapped['SaleReturn'] = relationship('SaleReturn', back_populates='items')

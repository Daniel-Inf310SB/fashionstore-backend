"""CU77: registro independiente del cambio, pago presencial y su idempotencia."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class SaleExchange(Base):
    __tablename__ = "sale_exchanges"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_exchange_positive_quantity"),
        CheckConstraint("original_paid_total >= 0 AND replacement_total >= 0 AND additional_paid >= 0", name="ck_sale_exchange_amounts"),
        CheckConstraint("additional_paid = 0 OR payment_method = 'CASH'", name="ck_sale_exchange_cash_payment"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    client_operation_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    exchange_code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='RESTRICT'), nullable=False, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey('sales.id', ondelete='RESTRICT'), nullable=False, index=True)
    sale_item_id: Mapped[int] = mapped_column(ForeignKey('sale_items.id', ondelete='RESTRICT'), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey('branches.id', ondelete='RESTRICT'), nullable=False)
    cashier_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    original_variant_id: Mapped[int] = mapped_column(ForeignKey('product_variants.id', ondelete='RESTRICT'), nullable=False)
    replacement_variant_id: Mapped[int] = mapped_column(ForeignKey('product_variants.id', ondelete='RESTRICT'), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    original_paid_total: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    replacement_total: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    additional_paid: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(20))
    item_condition: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class ReturnInspection(Base):
    __tablename__ = 'return_inspections'
    __table_args__ = (
        UniqueConstraint('return_item_id', name='uq_return_inspection_item'),
        CheckConstraint("decision IN ('RESTOCKED', 'DAMAGED')", name='ck_return_inspection_decision'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    return_item_id: Mapped[int] = mapped_column(ForeignKey('return_items.id', ondelete='RESTRICT'), nullable=False, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='RESTRICT'), nullable=False)
    inspector_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False)
    movement_id: Mapped[int | None] = mapped_column(ForeignKey('inventory_movements.id', ondelete='RESTRICT'), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

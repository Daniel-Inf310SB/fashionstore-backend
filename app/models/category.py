from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey as TenantForeignKey
from sqlalchemy import UniqueConstraint as TenantUniqueConstraint
from app.database.base import Base

class Category(Base):
    __tablename__ = "categories"

    __table_args__ = (
        TenantUniqueConstraint("tenant_id", "name", name="uq_categories_tenant_name"),
    )
    tenant = relationship("Tenant")

    # Empresa propietaria del registro.
    tenant_id: Mapped[int | None] = mapped_column(
        TenantForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    products = relationship("Product", back_populates="category")

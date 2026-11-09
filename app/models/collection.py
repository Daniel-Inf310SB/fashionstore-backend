from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey as TenantForeignKey
from sqlalchemy import UniqueConstraint as TenantUniqueConstraint
from app.database.base import Base

class Collection(Base):
    __tablename__ = "collections"

    __table_args__ = (
        TenantUniqueConstraint("tenant_id", "name", name="uq_collections_tenant_name"),
    )
    tenant = relationship("Tenant")

    # Empresa propietaria del registro.
    tenant_id: Mapped[int | None] = mapped_column(
        TenantForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    launch_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    product_links = relationship("ProductCollection", back_populates="collection", cascade="all, delete-orphan")

from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Uuid,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from sqlalchemy import UniqueConstraint as TenantUniqueConstraint
from app.database.base import Base


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        TenantUniqueConstraint("tenant_id", "code", name="uq_products_tenant_code"),
    )

    tenant = relationship("Tenant")

    # Empresa propietaria del registro.
    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    public_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), default=uuid4, nullable=False, unique=True, index=True)

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    brand: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    base_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    cover_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    cover_image_public_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    audience_id: Mapped[int] = mapped_column(
        ForeignKey(
            "audiences.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # =========================================================
    # RELACIONES
    # =========================================================

    category = relationship(
        "Category",
        back_populates="products",
    )

    audience = relationship(
        "Audience",
        back_populates="products",
    )

    variants = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    virtual_fitting_assets = relationship(
        "VirtualFittingAsset",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    season_links = relationship(
        "ProductSeason",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    collection_links = relationship(
        "ProductCollection",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    promotion_links = relationship(
        "ProductPromotion",
        back_populates="product",
        cascade="all, delete-orphan",
    )
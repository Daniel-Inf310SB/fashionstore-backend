from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class VirtualFittingAsset(Base):
    __tablename__ = "virtual_fitting_assets"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    color_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "colors.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    asset_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    asset_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PNG_OVERLAY",
    )

    garment_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
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

    product = relationship(
        "Product",
        back_populates="virtual_fitting_assets",
    )

    color = relationship(
        "Color",
    )
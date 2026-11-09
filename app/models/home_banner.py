"""Campañas visuales del escaparate, aisladas por empresa."""
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class HomeBanner(Base):
    __tablename__ = "home_banners"
    __table_args__ = (
        CheckConstraint("target_type IN ('catalog', 'product', 'category', 'collection', 'promotion')", name="ck_home_banner_target_type"),
        Index("ix_home_banners_tenant_active_order", "tenant_id", "is_active", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(250))
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    mobile_image_url: Mapped[str | None] = mapped_column(String(500))
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default="catalog")
    target_id: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    show_as_popup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    popup_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

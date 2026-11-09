from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    # =====================================================
    # IDENTIFICACION
    # =====================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # =====================================================
    # INFORMACION EMPRESARIAL
    # =====================================================

    legal_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    tax_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # =====================================================
    # ESTADO
    # =====================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # =====================================================
    # AUDITORIA
    # =====================================================

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

    # =====================================================
    # RELACIONES
    # =====================================================

    users = relationship(
        "User",
        back_populates="tenant",
    )

    branches = relationship(
        "Branch",
        back_populates="tenant",
    )

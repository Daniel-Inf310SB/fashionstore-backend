
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class PlatformAdmin(Base):
    __tablename__ = "platform_admins"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_platform_admin_user",
        ),
    )

    # =====================================================
    # IDENTIFICACIÓN
    # =====================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # =====================================================
    # USUARIO SUPER ADMIN
    # =====================================================

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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
    # AUDITORÍA
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

    user = relationship(
        "User",
        back_populates="platform_admin",
        foreign_keys=[user_id],
    )

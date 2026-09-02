from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class AuditLog(Base):
    """
    Bitácora general de auditoría de FashionStore.

    Registra operaciones relevantes realizadas por usuarios
    o procesos del sistema.

    Ejemplos:
        CREATE_USER
        UPDATE_USER
        DEACTIVATE_USER
        CREATE_ROLE
        UPDATE_ROLE
        ASSIGN_ROLE_PERMISSIONS
        CREATE_PRODUCT
        UPDATE_INVENTORY
        LOGIN
        LOGOUT
    """

    __tablename__ = "audit_logs"


    # =========================================================
    # ID
    # =========================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )


    # =========================================================
    # USUARIO QUE REALIZÓ LA ACCIÓN
    # =========================================================

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )


    # =========================================================
    # ACCIÓN
    # =========================================================

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )


    # =========================================================
    # MÓDULO
    # =========================================================

    module: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )


    # =========================================================
    # ENTIDAD AFECTADA
    # =========================================================

    entity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )


    # =========================================================
    # DESCRIPCIÓN LEGIBLE
    # =========================================================

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


    # =========================================================
    # VALORES ANTES Y DESPUÉS
    # =========================================================

    old_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    new_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )


    # =========================================================
    # INFORMACIÓN DE LA PETICIÓN
    # =========================================================

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )


    # =========================================================
    # RESULTADO
    # =========================================================

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="SUCCESS",
        server_default="SUCCESS",
        index=True,
    )


    # =========================================================
    # FECHA
    # =========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


    # =========================================================
    # RELACIÓN
    # =========================================================

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="audit_logs",
    )


    # =========================================================
    # REPRESENTACIÓN
    # =========================================================

    def __repr__(self) -> str:

        return (
            f"<AuditLog("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"action={self.action!r}, "
            f"module={self.module!r}, "
            f"entity_type={self.entity_type!r}, "
            f"entity_id={self.entity_id}"
            f")>"
        )
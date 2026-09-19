from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class NotificationPushDelivery(Base):
    """
    Outbox de entrega push.

    La notificación interna se guarda primero. Esta tabla registra
    la entrega FCM por dispositivo y permite reintentos sin romper
    pedidos, reservas o pagos.
    """

    __tablename__ = "notification_push_deliveries"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    notification_id: Mapped[int] = mapped_column(
        ForeignKey(
            "notifications.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_device_id: Mapped[int] = mapped_column(
        ForeignKey(
            "user_devices.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    firebase_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    notification = relationship(
        "Notification",
        back_populates="push_deliveries",
    )

    user_device = relationship(
        "UserDevice",
    )

    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "user_device_id",
            name="uq_notification_push_delivery",
        ),
        Index(
            "ix_notification_push_delivery_pending",
            "status",
            "next_attempt_at",
        ),
    )

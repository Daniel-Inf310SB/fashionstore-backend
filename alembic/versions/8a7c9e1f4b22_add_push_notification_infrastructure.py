"""add push notification infrastructure

Revision ID: 8a7c9e1f4b22
Revises: 5fbf7c14cbfa
Create Date: 2026-09-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a7c9e1f4b22"
down_revision: Union[str, Sequence[str], None] = "5fbf7c14cbfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column(
            "target_type",
            sa.String(length=30),
            nullable=False,
            server_default="ALL_CUSTOMERS",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "dedupe_key",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dedupe_key",
            name="uq_notification_campaigns_dedupe_key",
        ),
    )

    op.create_index(
        "ix_notification_campaigns_campaign_type",
        "notification_campaigns",
        ["campaign_type"],
    )
    op.create_index(
        "ix_notification_campaigns_entity_id",
        "notification_campaigns",
        ["entity_id"],
    )
    op.create_index(
        "ix_notification_campaigns_status",
        "notification_campaigns",
        ["status"],
    )
    op.create_index(
        "ix_notification_campaigns_scheduled_for",
        "notification_campaigns",
        ["scheduled_for"],
    )
    op.create_index(
        "ix_notification_campaigns_dedupe_key",
        "notification_campaigns",
        ["dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ix_notification_campaign_due",
        "notification_campaigns",
        ["status", "scheduled_for"],
    )

    op.create_table(
        "notification_push_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("user_device_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "firebase_message_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_device_id"],
            ["user_devices.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id",
            "user_device_id",
            name="uq_notification_push_delivery",
        ),
    )

    op.create_index(
        "ix_notification_push_deliveries_notification_id",
        "notification_push_deliveries",
        ["notification_id"],
    )
    op.create_index(
        "ix_notification_push_deliveries_user_device_id",
        "notification_push_deliveries",
        ["user_device_id"],
    )
    op.create_index(
        "ix_notification_push_deliveries_status",
        "notification_push_deliveries",
        ["status"],
    )
    op.create_index(
        "ix_notification_push_deliveries_next_attempt_at",
        "notification_push_deliveries",
        ["next_attempt_at"],
    )
    op.create_index(
        "ix_notification_push_delivery_pending",
        "notification_push_deliveries",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_push_delivery_pending",
        table_name="notification_push_deliveries",
    )
    op.drop_index(
        "ix_notification_push_deliveries_next_attempt_at",
        table_name="notification_push_deliveries",
    )
    op.drop_index(
        "ix_notification_push_deliveries_status",
        table_name="notification_push_deliveries",
    )
    op.drop_index(
        "ix_notification_push_deliveries_user_device_id",
        table_name="notification_push_deliveries",
    )
    op.drop_index(
        "ix_notification_push_deliveries_notification_id",
        table_name="notification_push_deliveries",
    )
    op.drop_table("notification_push_deliveries")

    op.drop_index(
        "ix_notification_campaign_due",
        table_name="notification_campaigns",
    )
    op.drop_index(
        "ix_notification_campaigns_dedupe_key",
        table_name="notification_campaigns",
    )
    op.drop_index(
        "ix_notification_campaigns_scheduled_for",
        table_name="notification_campaigns",
    )
    op.drop_index(
        "ix_notification_campaigns_status",
        table_name="notification_campaigns",
    )
    op.drop_index(
        "ix_notification_campaigns_entity_id",
        table_name="notification_campaigns",
    )
    op.drop_index(
        "ix_notification_campaigns_campaign_type",
        table_name="notification_campaigns",
    )
    op.drop_table("notification_campaigns")

"""create notifications table actual

Revision ID: 5fbf7c14cbfa
Revises: 89e465563b75
Create Date: 2026-09-18 15:43:17.321708

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fbf7c14cbfa'
down_revision: Union[str, Sequence[str], None] = '89e465563b75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notifications',

        sa.Column(
            'id',
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            'user_id',
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            'type',
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            'event',
            sa.String(length=80),
            nullable=False,
        ),

        sa.Column(
            'title',
            sa.String(length=180),
            nullable=False,
        ),

        sa.Column(
            'message',
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            'entity_type',
            sa.String(length=40),
            nullable=True,
        ),

        sa.Column(
            'entity_id',
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            'action_url',
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            'dedupe_key',
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            'is_read',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),

        sa.Column(
            'read_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE',
        ),

        sa.UniqueConstraint(
            'dedupe_key',
            name='uq_notifications_dedupe_key',
        ),
    )

    op.create_index(
        'ix_notifications_user_id',
        'notifications',
        ['user_id'],
    )

    op.create_index(
        'ix_notifications_type',
        'notifications',
        ['type'],
    )

    op.create_index(
        'ix_notifications_event',
        'notifications',
        ['event'],
    )

    op.create_index(
        'ix_notifications_entity_type',
        'notifications',
        ['entity_type'],
    )

    op.create_index(
        'ix_notifications_entity_id',
        'notifications',
        ['entity_id'],
    )

    op.create_index(
        'ix_notifications_is_read',
        'notifications',
        ['is_read'],
    )

    op.create_index(
        'ix_notifications_created_at',
        'notifications',
        ['created_at'],
    )

    op.create_index(
        'ix_notifications_user_unread_created',
        'notifications',
        [
            'user_id',
            'is_read',
            'created_at',
        ],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_notifications_user_unread_created',
        table_name='notifications',
    )

    op.drop_index(
        'ix_notifications_created_at',
        table_name='notifications',
    )

    op.drop_index(
        'ix_notifications_is_read',
        table_name='notifications',
    )

    op.drop_index(
        'ix_notifications_entity_id',
        table_name='notifications',
    )

    op.drop_index(
        'ix_notifications_entity_type',
        table_name='notifications',
    )

    op.drop_index(
        'ix_notifications_event',
        table_name='notifications',
    )

    op.drop_index(
        'ix_notifications_type',
        table_name='notifications',
    )

    op.drop_index(
        'ix_notifications_user_id',
        table_name='notifications',
    )

    op.drop_table('notifications')
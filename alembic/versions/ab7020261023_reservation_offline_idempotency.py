"""CU70: operación idempotente para reservas offline.

Revision ID: ab7020261023
Revises: 759602436674, e72d20261016
"""
from alembic import op
import sqlalchemy as sa

revision = "ab7020261023"
down_revision = ("759602436674", "e72d20261016")
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("reservations", sa.Column("client_operation_id", sa.String(length=36), nullable=True))
    op.add_column("reservations", sa.Column("client_operation_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_reservations_client_operation_id", "reservations", ["client_operation_id"], unique=True)


def downgrade():
    op.drop_index("ix_reservations_client_operation_id", table_name="reservations")
    op.drop_column("reservations", "client_operation_hash")
    op.drop_column("reservations", "client_operation_id")

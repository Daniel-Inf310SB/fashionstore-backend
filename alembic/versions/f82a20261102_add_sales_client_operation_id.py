"""Add idempotency key to sales for offline sync.

Revision ID: f82a20261102
Revises: c77a20261023
"""
from alembic import op
import sqlalchemy as sa

revision = "f82a20261102"
down_revision = "c77a20261023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales", sa.Column("client_operation_id", sa.String(length=36), nullable=True))
    op.create_index(
        "ix_sales_client_operation_id", "sales", ["client_operation_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_sales_client_operation_id", table_name="sales")
    op.drop_column("sales", "client_operation_id")

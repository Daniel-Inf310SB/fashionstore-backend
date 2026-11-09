"""Create receipt table for safe offline cart transfer replays.

Revision ID: b47c20261105
Revises: a93b20261102
"""
from alembic import op
import sqlalchemy as sa

revision = "b47c20261105"
down_revision = "a93b20261102"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cart_offline_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_operation_id", sa.String(length=36), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("product_variant_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_cart_offline_customer_operation", "cart_offline_operations", ["customer_id", "client_operation_id"], unique=True)


def downgrade():
    op.drop_index("uq_cart_offline_customer_operation", table_name="cart_offline_operations")
    op.drop_table("cart_offline_operations")

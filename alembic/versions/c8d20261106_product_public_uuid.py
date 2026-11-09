"""Add stable UUID public identifiers for products.

Revision ID: c8d20261106
Revises: c7d20261106
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d20261106"
down_revision = "c7d20261106"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("products", sa.Column("public_id", sa.Uuid(as_uuid=True), nullable=True, server_default=sa.text("gen_random_uuid()")))
    op.execute("UPDATE products SET public_id = gen_random_uuid() WHERE public_id IS NULL")
    op.alter_column("products", "public_id", nullable=False)
    op.create_index("ix_products_public_id", "products", ["public_id"], unique=True)

def downgrade():
    op.drop_index("ix_products_public_id", table_name="products")
    op.drop_column("products", "public_id")

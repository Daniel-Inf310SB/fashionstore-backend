"""Banners por tenant para escaparate móvil.

Revision ID: c6d20261106
Revises: b47c20261105
"""
from alembic import op
import sqlalchemy as sa

revision = "c6d20261106"
down_revision = "b47c20261105"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "home_banners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("subtitle", sa.String(250)),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("mobile_image_url", sa.String(500)),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Integer()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_type IN ('catalog', 'product', 'category', 'collection', 'promotion')", name="ck_home_banner_target_type"),
    )
    op.create_index("ix_home_banners_tenant_id", "home_banners", ["tenant_id"])
    op.create_index("ix_home_banners_tenant_active_order", "home_banners", ["tenant_id", "is_active", "sort_order"])


def downgrade():
    op.drop_index("ix_home_banners_tenant_active_order", table_name="home_banners")
    op.drop_index("ix_home_banners_tenant_id", table_name="home_banners")
    op.drop_table("home_banners")

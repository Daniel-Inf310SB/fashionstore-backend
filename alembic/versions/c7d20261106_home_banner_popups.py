"""Configure highlighted popups for home banners.

Revision ID: c7d20261106
Revises: c6d20261106
"""
from alembic import op
import sqlalchemy as sa

revision = "c7d20261106"
down_revision = "c6d20261106"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("home_banners", sa.Column("show_as_popup", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("home_banners", sa.Column("popup_priority", sa.Integer(), nullable=False, server_default="0"))

def downgrade():
    op.drop_column("home_banners", "popup_priority")
    op.drop_column("home_banners", "show_as_popup")

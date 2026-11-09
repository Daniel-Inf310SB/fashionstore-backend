"""Programación de cambio de plan sin alterar el período pagado.

Revision ID: e72d20261016
Revises: c9ab20261016
"""
from alembic import op
import sqlalchemy as sa
revision = "e72d20261016"
down_revision = "c9ab20261016"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("tenant_subscriptions", sa.Column("pending_plan_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_tenant_subscription_pending_plan", "tenant_subscriptions", "subscription_plans", ["pending_plan_id"], ["id"], ondelete="RESTRICT")

def downgrade():
    op.drop_constraint("fk_tenant_subscription_pending_plan", "tenant_subscriptions", type_="foreignkey")
    op.drop_column("tenant_subscriptions", "pending_plan_id")

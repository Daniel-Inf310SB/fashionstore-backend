"""SaaS subscription billing and duration.

Revision ID: c9ab20261016
Revises: a46e2b00plans
"""
from alembic import op
import sqlalchemy as sa

revision = "c9ab20261016"
down_revision = "a46e2b00plans"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenant_subscriptions", sa.Column("duration_months", sa.Integer(), nullable=True))
    op.add_column("tenant_subscriptions", sa.Column("price_snapshot", sa.Numeric(12, 2), nullable=True))
    op.add_column("tenant_subscriptions", sa.Column("currency_snapshot", sa.String(3), nullable=True))
    op.create_table("subscription_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("tenant_subscriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.UniqueConstraint("reference", name="uq_subscription_payment_reference"),
        sa.CheckConstraint("duration_months IN (1, 3, 6, 12)", name="ck_subscription_payment_months"),
        sa.CheckConstraint("amount >= 0", name="ck_subscription_payment_amount"),
    )
    op.create_index("ix_subscription_payments_subscription_id", "subscription_payments", ["subscription_id"])


def downgrade():
    op.drop_index("ix_subscription_payments_subscription_id", table_name="subscription_payments")
    op.drop_table("subscription_payments")
    op.drop_column("tenant_subscriptions", "currency_snapshot")
    op.drop_column("tenant_subscriptions", "price_snapshot")
    op.drop_column("tenant_subscriptions", "duration_months")

"""Add SaaS plans and tenant subscriptions.

Revision ID: a46e2b00plans
Revises: d7e2b9a13f60
"""
from alembic import op
import sqlalchemy as sa

revision = 'a46e2b00plans'
down_revision = 'd7e2b9a13f60'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('subscription_plans',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('code',sa.String(50),nullable=False),
        sa.Column('name',sa.String(100),nullable=False),
        sa.Column('description',sa.String(500),nullable=True),
        sa.Column('monthly_price',sa.Numeric(12,2),nullable=False),
        sa.Column('currency',sa.String(3),nullable=False,server_default='BOB'),
        sa.Column('max_branches',sa.Integer(),nullable=True),
        sa.Column('max_staff',sa.Integer(),nullable=True),
        sa.Column('features',sa.JSON(),nullable=False),
        sa.Column('is_active',sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('code',name='uq_subscription_plan_code'))
    op.create_index('ix_subscription_plans_code','subscription_plans',['code'],unique=True)
    op.create_table('tenant_subscriptions',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('tenant_id',sa.Integer(),sa.ForeignKey('tenants.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('plan_id',sa.Integer(),sa.ForeignKey('subscription_plans.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),
        sa.Column('starts_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id',name='uq_tenant_subscription_current'))
    op.create_index('ix_tenant_subscriptions_tenant_id','tenant_subscriptions',['tenant_id'])

def downgrade():
    op.drop_index('ix_tenant_subscriptions_tenant_id',table_name='tenant_subscriptions')
    op.drop_table('tenant_subscriptions')
    op.drop_index('ix_subscription_plans_code',table_name='subscription_plans')
    op.drop_table('subscription_plans')

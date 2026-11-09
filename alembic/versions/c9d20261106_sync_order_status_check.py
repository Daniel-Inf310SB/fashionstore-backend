"""Align orders status check constraint with Order model and status transitions.

Revision ID: c9d20261106
Revises: c8d20261106
"""
from alembic import op
import sqlalchemy as sa

revision = 'c9d20261106'
down_revision = 'c8d20261106'
branch_labels = None
depends_on = None

# Keep in sync with app.models.order.Order.__table_args__.
CURRENT_STATUSES = (
    'PENDING_PAYMENT', 'PAYMENT_FAILED', 'PAID', 'PREPARING',
    'READY_FOR_PICKUP', 'SHIPPED', 'DELIVERED', 'COMPLETED',
    'CANCELLED', 'REFUNDED',
)
PREVIOUS_STATUSES = (
    'PENDING_PAYMENT', 'PAID', 'PROCESSING', 'READY',
    'COMPLETED', 'CANCELLED', 'PAYMENT_FAILED',
)


def _constraint(statuses):
    return 'status IN (' + ', '.join("'" + s + "'" for s in statuses) + ')'


def upgrade():
    # The migration is transactional in PostgreSQL. If unexpected legacy
    # statuses exist, creating the new constraint fails safely without
    # silently rewriting order/payment state.
    op.drop_constraint('ck_order_status', 'orders', type_='check')
    op.create_check_constraint('ck_order_status', 'orders', _constraint(CURRENT_STATUSES))


def downgrade():
    # Do not silently rewrite any newer status during downgrade.
    op.drop_constraint('ck_order_status', 'orders', type_='check')
    op.create_check_constraint('ck_order_status', 'orders', _constraint(PREVIOUS_STATUSES))

"""Devoluciones presenciales y trazabilidad separada de returns online.

Revision ID: d0d20261106
Revises: c9d20261106
"""
from alembic import op
import sqlalchemy as sa
revision = 'd0d20261106'
down_revision = 'c9d20261106'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('sale_returns',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('tenant_id',sa.Integer(),sa.ForeignKey('tenants.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('branch_id',sa.Integer(),sa.ForeignKey('branches.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('sale_id',sa.Integer(),sa.ForeignKey('sales.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('customer_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('status',sa.String(24),nullable=False,server_default='REQUESTED'),
        sa.Column('reason',sa.String(500),nullable=False),
        sa.Column('staff_note',sa.String(500)),
        sa.Column('requested_amount',sa.Numeric(12,2),nullable=False),
        sa.Column('reviewed_by',sa.Integer(),sa.ForeignKey('users.id',ondelete='SET NULL')),
        sa.Column('received_by',sa.Integer(),sa.ForeignKey('users.id',ondelete='SET NULL')),
        sa.Column('inspected_by',sa.Integer(),sa.ForeignKey('users.id',ondelete='SET NULL')),
        sa.Column('refunded_by',sa.Integer(),sa.ForeignKey('users.id',ondelete='SET NULL')),
        sa.Column('refund_mode',sa.String(24)),sa.Column('refund_reference',sa.String(150)),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column('reviewed_at',sa.DateTime(timezone=True)),
        sa.Column('received_at',sa.DateTime(timezone=True)),
        sa.Column('inspected_at',sa.DateTime(timezone=True)),
        sa.Column('refunded_at',sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('REQUESTED','APPROVED','REJECTED','RECEIVED','INSPECTED','REFUNDED','CANCELLED')",name='ck_sale_return_status'),
        sa.CheckConstraint('requested_amount >= 0',name='ck_sale_return_amount'))
    for name in ('tenant_id','branch_id','sale_id','customer_id'):
        op.create_index(f'ix_sale_returns_{name}','sale_returns',[name])
    op.create_table('sale_return_items',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('sale_return_id',sa.Integer(),sa.ForeignKey('sale_returns.id',ondelete='CASCADE'),nullable=False),
        sa.Column('sale_item_id',sa.Integer(),sa.ForeignKey('sale_items.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('quantity',sa.Integer(),nullable=False),
        sa.Column('condition',sa.String(16)),
        sa.UniqueConstraint('sale_return_id','sale_item_id',name='uq_sale_return_item'),
        sa.CheckConstraint('quantity > 0',name='ck_sale_return_item_qty'))
    op.create_index('ix_sale_return_items_sale_return_id','sale_return_items',['sale_return_id'])

def downgrade():
    op.drop_table('sale_return_items')
    op.drop_table('sale_returns')

"""CU77 cambios de prendas, transacciones presenciales auditables.

Revision ID: c77a20261023
Revises: ab7020261023
"""
from alembic import op
import sqlalchemy as sa
revision = 'c77a20261023'
down_revision = 'ab7020261023'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('sale_exchanges',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('client_operation_id',sa.String(36),nullable=False),
        sa.Column('exchange_code',sa.String(60),nullable=False),
        sa.Column('tenant_id',sa.Integer(),sa.ForeignKey('tenants.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('sale_id',sa.Integer(),sa.ForeignKey('sales.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('sale_item_id',sa.Integer(),sa.ForeignKey('sale_items.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('branch_id',sa.Integer(),sa.ForeignKey('branches.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('cashier_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('original_variant_id',sa.Integer(),sa.ForeignKey('product_variants.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('replacement_variant_id',sa.Integer(),sa.ForeignKey('product_variants.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('quantity',sa.Integer(),nullable=False),
        sa.Column('original_paid_total',sa.Numeric(12,2),nullable=False),
        sa.Column('replacement_total',sa.Numeric(12,2),nullable=False),
        sa.Column('additional_paid',sa.Numeric(12,2),nullable=False),
        sa.Column('payment_method',sa.String(20)),
        sa.Column('item_condition',sa.String(20),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint('quantity > 0', name='ck_sale_exchange_positive_quantity'),
        sa.CheckConstraint('original_paid_total >= 0 AND replacement_total >= 0 AND additional_paid >= 0',name='ck_sale_exchange_amounts'),
        sa.CheckConstraint("additional_paid = 0 OR payment_method = 'CASH'",name='ck_sale_exchange_cash_payment'),
        sa.UniqueConstraint('exchange_code'))
    for col in ('client_operation_id','tenant_id','sale_id','sale_item_id'):
        op.create_index('ix_sale_exchanges_'+col, 'sale_exchanges', [col], unique=(col=='client_operation_id'))

def downgrade():
    op.drop_table('sale_exchanges')

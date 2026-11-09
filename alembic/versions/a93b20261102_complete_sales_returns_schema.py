"""Complete missing sales reservation relationship and return workflow tables.

Revision ID: a93b20261102
Revises: f82a20261102
"""
from alembic import op
import sqlalchemy as sa

revision = "a93b20261102"
down_revision = "f82a20261102"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sales", sa.Column("reservation_id", sa.Integer(), nullable=True))
    op.create_index("ix_sales_reservation_id", "sales", ["reservation_id"], unique=True)
    op.create_foreign_key("fk_sales_reservation_id_reservations", "sales", "reservations", ["reservation_id"], ["id"], ondelete="RESTRICT")

    op.create_table(
        "return_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("admin_note", sa.String(500)),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("received_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('REQUESTED','APPROVED','REJECTED','RECEIVED','CANCELLED')", name="ck_return_status"),
    )
    for field in ("tenant_id", "order_id", "customer_id"):
        op.create_index(f"ix_return_requests_{field}", "return_requests", [field])

    op.create_table(
        "return_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_request_id", sa.Integer(), sa.ForeignKey("return_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.UniqueConstraint("return_request_id", "order_item_id", name="uq_return_order_item"),
        sa.CheckConstraint("quantity > 0", name="ck_return_quantity_positive"),
    )
    op.create_index("ix_return_items_return_request_id", "return_items", ["return_request_id"])

    op.create_table(
        "return_refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_request_id", sa.Integer(), sa.ForeignKey("return_requests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("stripe_refund_id", sa.String(150)),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("failure_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("return_request_id", name="uq_refund_return_request"),
        sa.UniqueConstraint("idempotency_key", name="uq_refund_idempotency"),
        sa.UniqueConstraint("stripe_refund_id", name="uq_refund_stripe_id"),
        sa.CheckConstraint("amount > 0", name="ck_return_refund_positive"),
        sa.CheckConstraint("status IN ('PREPARED','PROCESSING','SUCCEEDED','FAILED','MANUAL_REVIEW')", name="ck_return_refund_status"),
    )

    op.create_table(
        "return_inspections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_item_id", sa.Integer(), sa.ForeignKey("return_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("inspector_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column("movement_id", sa.Integer(), sa.ForeignKey("inventory_movements.id", ondelete="RESTRICT"), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("return_item_id", name="uq_return_inspection_item"),
        sa.CheckConstraint("decision IN ('RESTOCKED', 'DAMAGED')", name="ck_return_inspection_decision"),
    )
    op.create_index("ix_return_inspections_return_item_id", "return_inspections", ["return_item_id"])

    # Extra non-destructive indexes flagged by the initial check.
    for table, field, unique in [
        ("categories", "name", False), ("collections", "name", False),
        ("notification_campaigns", "id", False), ("notification_push_deliveries", "id", False),
        ("notifications", "id", False), ("products", "code", False),
        ("suppliers", "nit", False),
    ]:
        op.create_index(f"ix_{table}_{field}", table, [field], unique=unique)
    # Existing unique constraints are intentionally retained.
    op.create_index("ix_notifications_dedupe_key", "notifications", ["dedupe_key"], unique=True)


def downgrade():
    op.drop_index("ix_notifications_dedupe_key", table_name="notifications")
    for table, field in [
        ("suppliers", "nit"), ("products", "code"), ("notifications", "id"),
        ("notification_push_deliveries", "id"), ("notification_campaigns", "id"),
        ("collections", "name"), ("categories", "name"),
    ]:
        op.drop_index(f"ix_{table}_{field}", table_name=table)
    op.drop_index("ix_return_inspections_return_item_id", table_name="return_inspections")
    op.drop_table("return_inspections")
    op.drop_table("return_refunds")
    op.drop_index("ix_return_items_return_request_id", table_name="return_items")
    op.drop_table("return_items")
    for field in ("tenant_id", "order_id", "customer_id"):
        op.drop_index(f"ix_return_requests_{field}", table_name="return_requests")
    op.drop_table("return_requests")
    op.drop_constraint("fk_sales_reservation_id_reservations", "sales", type_="foreignkey")
    op.drop_index("ix_sales_reservation_id", table_name="sales")
    op.drop_column("sales", "reservation_id")

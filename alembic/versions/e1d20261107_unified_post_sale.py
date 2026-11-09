"""Unified after-sales cases for online and POS transactions.

Revision ID: e1d20261107
Revises: d0d20261106
"""
from alembic import op
import sqlalchemy as sa

revision = "e1d20261107"
down_revision = "d0d20261106"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_sale_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_code", sa.String(60), nullable=False),
        sa.Column("idempotency_key", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_channel", sa.String(10), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("resolution_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(28), nullable=False, server_default="REQUESTED"),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("staff_note", sa.String(1000)),
        sa.Column("original_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("replacement_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("difference_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("settlement_kind", sa.String(16), nullable=False, server_default="NONE"),
        sa.Column("settlement_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("settlement_status", sa.String(16), nullable=False, server_default="NOT_REQUIRED"),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("received_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("inspected_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("completed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("inspected_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "(source_channel = 'ONLINE' AND order_id IS NOT NULL AND sale_id IS NULL) OR "
            "(source_channel = 'POS' AND sale_id IS NOT NULL AND order_id IS NULL)",
            name="ck_post_sale_case_single_source",
        ),
        sa.CheckConstraint("source_channel IN ('ONLINE','POS')", name="ck_post_sale_case_channel"),
        sa.CheckConstraint("resolution_type IN ('REFUND','EXCHANGE')", name="ck_post_sale_case_resolution"),
        sa.CheckConstraint(
            "status IN ('REQUESTED','APPROVED','REJECTED','RECEIVED','INSPECTED','AWAITING_SETTLEMENT','COMPLETED','CANCELLED')",
            name="ck_post_sale_case_status",
        ),
        sa.CheckConstraint(
            "original_amount >= 0 AND replacement_amount >= 0 AND settlement_amount >= 0",
            name="ck_post_sale_case_amounts",
        ),
        sa.CheckConstraint("settlement_kind IN ('NONE','COLLECT','REFUND')", name="ck_post_sale_case_settlement_kind"),
        sa.CheckConstraint("settlement_status IN ('NOT_REQUIRED','PENDING','PROCESSING','COMPLETED','FAILED','MANUAL_REVIEW')", name="ck_post_sale_case_settlement_status"),
        sa.UniqueConstraint("case_code", name="uq_post_sale_case_code"),
        sa.UniqueConstraint("idempotency_key", name="uq_post_sale_case_idempotency"),
    )
    for col in ("tenant_id", "customer_id", "branch_id", "order_id", "sale_id", "status"):
        op.create_index(f"ix_post_sale_cases_{col}", "post_sale_cases", [col])

    op.create_table(
        "post_sale_case_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("post_sale_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="RESTRICT")),
        sa.Column("sale_item_id", sa.Integer(), sa.ForeignKey("sale_items.id", ondelete="RESTRICT")),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("original_unit_paid", sa.Numeric(12, 2), nullable=False),
        sa.Column("original_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("condition", sa.String(16)),
        sa.Column("inspection_note", sa.String(500)),
        sa.Column("inventory_movement_id", sa.Integer(), sa.ForeignKey("inventory_movements.id", ondelete="RESTRICT"), unique=True),
        sa.CheckConstraint(
            "(order_item_id IS NOT NULL AND sale_item_id IS NULL) OR "
            "(sale_item_id IS NOT NULL AND order_item_id IS NULL)",
            name="ck_post_sale_case_item_single_source",
        ),
        sa.CheckConstraint("quantity > 0 AND original_unit_paid >= 0 AND original_total >= 0", name="ck_post_sale_case_item_amounts"),
        sa.CheckConstraint("condition IS NULL OR condition IN ('RESELLABLE','DAMAGED','QUARANTINE')", name="ck_post_sale_case_item_condition"),
        sa.UniqueConstraint("case_id", "order_item_id", name="uq_post_sale_case_order_item"),
        sa.UniqueConstraint("case_id", "sale_item_id", name="uq_post_sale_case_sale_item"),
    )
    op.create_index("ix_post_sale_case_items_case_id", "post_sale_case_items", ["case_id"])

    op.create_table(
        "post_sale_replacement_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("post_sale_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("inventory_movement_id", sa.Integer(), sa.ForeignKey("inventory_movements.id", ondelete="RESTRICT"), unique=True),
        sa.CheckConstraint("quantity > 0 AND unit_price >= 0 AND subtotal >= 0", name="ck_post_sale_replacement_amounts"),
        sa.UniqueConstraint("case_id", "product_variant_id", name="uq_post_sale_replacement_variant"),
    )
    op.create_index("ix_post_sale_replacement_items_case_id", "post_sale_replacement_items", ["case_id"])

    op.create_table(
        "post_sale_case_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("post_sale_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(28)),
        sa.Column("to_status", sa.String(28)),
        sa.Column("note", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_post_sale_case_events_case_id", "post_sale_case_events", ["case_id"])

    op.create_table(
        "post_sale_settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("post_sale_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BOB"),
        sa.Column("method", sa.String(20)),
        sa.Column("mode", sa.String(24)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reference", sa.String(150)),
        sa.Column("stripe_refund_id", sa.String(150)),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("completed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()),
        sa.CheckConstraint("kind IN ('COLLECT','REFUND')", name="ck_post_sale_settlement_kind"),
        sa.CheckConstraint("amount > 0", name="ck_post_sale_settlement_amount"),
        sa.CheckConstraint("status IN ('PROCESSING','COMPLETED','FAILED','MANUAL_REVIEW')", name="ck_post_sale_settlement_status"),
        sa.CheckConstraint("method IS NULL OR method IN ('CASH','CARD','QR','TRANSFER')", name="ck_post_sale_settlement_method"),
        sa.CheckConstraint("mode IS NULL OR mode IN ('BRANCH_COLLECTION','DEMO_LOCAL','EXTERNAL_MANUAL','STRIPE_TEST')", name="ck_post_sale_settlement_mode"),
        sa.UniqueConstraint("case_id", name="uq_post_sale_settlement_case"),
        sa.UniqueConstraint("idempotency_key", name="uq_post_sale_settlement_idempotency"),
        sa.UniqueConstraint("stripe_refund_id", name="uq_post_sale_settlement_stripe_refund"),
    )
    op.create_index("ix_post_sale_settlements_tenant_id", "post_sale_settlements", ["tenant_id"])


def downgrade():
    op.drop_table("post_sale_settlements")
    op.drop_table("post_sale_case_events")
    op.drop_table("post_sale_replacement_items")
    op.drop_table("post_sale_case_items")
    op.drop_table("post_sale_cases")

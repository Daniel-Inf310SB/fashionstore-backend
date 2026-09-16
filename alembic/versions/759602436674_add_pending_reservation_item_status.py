from alembic import op
import sqlalchemy as sa


# =========================================================
# ALEMBIC IDENTIFIERS
# =========================================================

revision = "759602436674"

down_revision = "3452536f4516"

branch_labels = None

depends_on = None


# =========================================================
# UPGRADE
# =========================================================

def upgrade() -> None:

    with op.batch_alter_table(
        "reservation_items",
    ) as batch_op:

        batch_op.drop_constraint(
            "ck_reservation_item_status",
            type_="check",
        )

        batch_op.create_check_constraint(
            "ck_reservation_item_status",
            """
            status IN (
                'PENDING',
                'RESERVED',
                'RELEASED',
                'CONSUMED'
            )
            """,
        )

        batch_op.alter_column(
            "status",
            existing_type=sa.String(
                length=20,
            ),
            server_default=sa.text(
                "'PENDING'",
            ),
            existing_nullable=False,
        )


# =========================================================
# DOWNGRADE
# =========================================================

def downgrade() -> None:

    with op.batch_alter_table(
        "reservation_items",
    ) as batch_op:

        batch_op.drop_constraint(
            "ck_reservation_item_status",
            type_="check",
        )

        batch_op.create_check_constraint(
            "ck_reservation_item_status",
            """
            status IN (
                'RESERVED',
                'RELEASED',
                'CONSUMED'
            )
            """,
        )

        batch_op.alter_column(
            "status",
            existing_type=sa.String(
                length=20,
            ),
            server_default=sa.text(
                "'RESERVED'",
            ),
            existing_nullable=False,
        )
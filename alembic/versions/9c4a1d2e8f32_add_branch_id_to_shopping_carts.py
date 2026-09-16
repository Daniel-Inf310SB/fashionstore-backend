"""add branch id to shopping carts

Revision ID: 9c4a1d2e8f32
Revises: 759602436674
Create Date: 2026-09-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c4a1d2e8f32"
down_revision: Union[str, None] = "759602436674"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        "shopping_carts",
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        op.f(
            "ix_shopping_carts_branch_id"
        ),
        "shopping_carts",
        [
            "branch_id",
        ],
        unique=False,
    )

    op.create_foreign_key(
        "fk_shopping_carts_branch_id_branches",
        "shopping_carts",
        "branches",
        [
            "branch_id",
        ],
        [
            "id",
        ],
        ondelete="SET NULL",
    )


def downgrade() -> None:

    op.drop_constraint(
        "fk_shopping_carts_branch_id_branches",
        "shopping_carts",
        type_="foreignkey",
    )

    op.drop_index(
        op.f(
            "ix_shopping_carts_branch_id"
        ),
        table_name=
            "shopping_carts",
    )

    op.drop_column(
        "shopping_carts",
        "branch_id",
    )

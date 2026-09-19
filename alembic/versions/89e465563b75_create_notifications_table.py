"""create notifications table

Revision ID: 89e465563b75
Revises: 61c79c1d2d01
Create Date: 2026-09-18 15:39:21.084771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89e465563b75'
down_revision: Union[str, Sequence[str], None] = '61c79c1d2d01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

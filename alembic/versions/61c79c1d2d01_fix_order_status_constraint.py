"""fix order status constraint

Revision ID: 61c79c1d2d01
Revises: 43d73512294a
Create Date: 2026-09-18 15:18:50.419537

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61c79c1d2d01'
down_revision: Union[str, Sequence[str], None] = '43d73512294a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

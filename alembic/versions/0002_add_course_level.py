"""add course level

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 00:22:45.110175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. a nullable column first: the existing rows get NULL
    op.add_column("courses", sa.Column("level", sa.Text(), nullable=True))
    # 2. fill the existing rows (a decision about data, not schema)
    op.execute(
        "UPDATE courses SET level = "
        "CASE WHEN is_elective THEN 'beginner' ELSE 'intermediate' END"
    )
    # 3. now every row has a value, so the column can be required
    op.alter_column("courses", "level", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("courses", "level")

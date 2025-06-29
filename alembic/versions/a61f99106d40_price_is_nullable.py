"""price is nullable

Revision ID: a61f99106d40
Revises: 6f0329c86ed4
Create Date: 2025-06-09 17:47:34.722521

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a61f99106d40"
down_revision: Union[str, None] = "6f0329c86ed4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "orders",
        "price",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "orders",
        "price",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
    )
    # ### end Alembic commands ###

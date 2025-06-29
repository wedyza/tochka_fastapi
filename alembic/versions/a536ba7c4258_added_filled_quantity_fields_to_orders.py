"""Added filled quantity fields to orders

Revision ID: a536ba7c4258
Revises: 7d1473f934af
Create Date: 2025-04-11 21:38:54.826782

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a536ba7c4258"
down_revision: Union[str, None] = "7d1473f934af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("orders", sa.Column("filled_quantity", sa.Float(), nullable=False))
    op.alter_column(
        "orders",
        "quantity",
        existing_type=sa.INTEGER(),
        type_=sa.Float(),
        existing_nullable=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "orders",
        "quantity",
        existing_type=sa.Float(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
    op.drop_column("orders", "filled_quantity")
    # ### end Alembic commands ###

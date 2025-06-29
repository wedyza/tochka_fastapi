"""empty message

Revision ID: 4c2ad5775e65
Revises: 9ae31518bd2b
Create Date: 2025-04-06 18:16:31.325066

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4c2ad5775e65"
down_revision: Union[str, None] = "9ae31518bd2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, "balance", "users", ["user_id"], ["id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "balance", type_="foreignkey")
    # ### end Alembic commands ###

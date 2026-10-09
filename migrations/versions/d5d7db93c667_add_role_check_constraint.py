"""add role check constraint

Revision ID: d5d7db93c667
Revises: d6e171a34ebd
Create Date: 2026-10-08 17:35:15.008422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5d7db93c667'
down_revision: Union[str, Sequence[str], None] = 'd6e171a34ebd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('user', 'admin')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_users_role",
        "users",
        type_="check",
    )

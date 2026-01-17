"""Add location_entered_at to game_states

Revision ID: g2c3d4e5f6a7
Revises: f1b2c3d4e5f6
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "g2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "f1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add location_entered_at column to game_states table."""
    if not _column_exists("game_states", "location_entered_at"):
        op.add_column(
            "game_states",
            sa.Column("location_entered_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    """Remove location_entered_at column from game_states table."""
    if _column_exists("game_states", "location_entered_at"):
        op.drop_column("game_states", "location_entered_at")

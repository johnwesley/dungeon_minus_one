"""Add requires_light column to locations

Revision ID: d9e5f6a7b8c9
Revises: c8d4e5f6a7b8
Create Date: 2025-12-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'd9e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c8d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    if not table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add requires_light column to locations table."""
    if not column_exists('locations', 'requires_light'):
        op.add_column(
            'locations',
            sa.Column('requires_light', sa.Boolean(), server_default='0', nullable=False)
        )


def downgrade() -> None:
    """Remove requires_light column from locations table."""
    if column_exists('locations', 'requires_light'):
        op.drop_column('locations', 'requires_light')

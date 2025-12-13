"""Add notifications tables

Revision ID: c8d4e5f6a7b8
Revises: b6bbe64b7cf9
Create Date: 2025-12-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c8d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b6bbe64b7cf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Create notifications and notification_dismissals tables."""
    if not table_exists('notifications'):
        op.create_table(
            'notifications',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('notification_type', sa.String(50), server_default='info'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_notifications_expires', 'notifications', ['expires_at'])

    if not table_exists('notification_dismissals'):
        op.create_table(
            'notification_dismissals',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('notification_id', sa.String(36), sa.ForeignKey('notifications.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('dismissed_at', sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index('idx_dismissals_user', 'notification_dismissals', ['user_id'])
        op.create_index('idx_dismissals_notification', 'notification_dismissals', ['notification_id'])


def downgrade() -> None:
    """Drop notifications tables."""
    if table_exists('notification_dismissals'):
        op.drop_index('idx_dismissals_notification', 'notification_dismissals')
        op.drop_index('idx_dismissals_user', 'notification_dismissals')
        op.drop_table('notification_dismissals')
    if table_exists('notifications'):
        op.drop_index('idx_notifications_expires', 'notifications')
        op.drop_table('notifications')

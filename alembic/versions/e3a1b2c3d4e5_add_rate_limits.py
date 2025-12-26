"""add rate limits

Revision ID: e3a1b2c3d4e5
Revises: d9e5f6a7b8c9
Create Date: 2025-12-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e3a1b2c3d4e5"
down_revision = "d9e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limits",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_rate_limits_expires_at", "rate_limits", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_rate_limits_expires_at", table_name="rate_limits")
    op.drop_table("rate_limits")

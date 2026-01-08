"""add bff auth tables

Revision ID: f1b2c3d4e5f6
Revises: e3a1b2c3d4e5
Create Date: 2026-01-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "f1b2c3d4e5f6"
down_revision = "e3a1b2c3d4e5"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(col.get("name") == column_name for col in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def _unique_exists(table_name: str, columns: list[str]) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = inspect(bind)
    for constraint in inspector.get_unique_constraints(table_name):
        if constraint.get("column_names") == columns:
            return True
    for idx in inspector.get_indexes(table_name):
        if idx.get("unique") and idx.get("column_names") == columns:
            return True
    return False


def upgrade() -> None:
    if _table_exists("users"):
        if not _column_exists("users", "email_normalized"):
            op.add_column("users", sa.Column("email_normalized", sa.String(length=255), nullable=True))
        if not _column_exists("users", "expires_at"):
            op.add_column("users", sa.Column("expires_at", sa.DateTime(), nullable=True))
        if not _column_exists("users", "suspended_at"):
            op.add_column("users", sa.Column("suspended_at", sa.DateTime(), nullable=True))
        if not _column_exists("users", "suspended_reason"):
            op.add_column("users", sa.Column("suspended_reason", sa.Text(), nullable=True))
        if not _column_exists("users", "deleted_at"):
            op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
        if not _unique_exists("users", ["email_normalized"]):
            op.create_unique_constraint("uq_users_email_normalized", "users", ["email_normalized"])
        if not _index_exists("users", "ix_users_expires_at"):
            op.create_index("ix_users_expires_at", "users", ["expires_at"], unique=False)

    if _table_exists("invite_codes"):
        if not _column_exists("invite_codes", "invite_email"):
            op.add_column("invite_codes", sa.Column("invite_email", sa.String(length=255), nullable=True))
        if not _column_exists("invite_codes", "invite_email_normalized"):
            op.add_column("invite_codes", sa.Column("invite_email_normalized", sa.String(length=255), nullable=True))
        if not _column_exists("invite_codes", "token_hash"):
            op.add_column("invite_codes", sa.Column("token_hash", sa.String(length=255), nullable=True))
        if not _column_exists("invite_codes", "expires_at"):
            op.add_column("invite_codes", sa.Column("expires_at", sa.DateTime(), nullable=True))
        if not _column_exists("invite_codes", "sent_at"):
            op.add_column("invite_codes", sa.Column("sent_at", sa.DateTime(), nullable=True))
        if not _column_exists("invite_codes", "revoked_at"):
            op.add_column("invite_codes", sa.Column("revoked_at", sa.DateTime(), nullable=True))
        if not _index_exists("invite_codes", "ix_invite_codes_invite_email"):
            op.create_index("ix_invite_codes_invite_email", "invite_codes", ["invite_email"], unique=False)
        if not _index_exists("invite_codes", "ix_invite_codes_invite_email_normalized"):
            op.create_index("ix_invite_codes_invite_email_normalized", "invite_codes", ["invite_email_normalized"], unique=False)
        if not _unique_exists("invite_codes", ["token_hash"]):
            op.create_unique_constraint("uq_invite_codes_token_hash", "invite_codes", ["token_hash"])
        if not _index_exists("invite_codes", "ix_invite_codes_expires_at"):
            op.create_index("ix_invite_codes_expires_at", "invite_codes", ["expires_at"], unique=False)
        if not _index_exists("invite_codes", "ix_invite_codes_revoked_at"):
            op.create_index("ix_invite_codes_revoked_at", "invite_codes", ["revoked_at"], unique=False)

    if not _table_exists("user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("csrf_token_hash", sa.String(length=255), nullable=False),
            sa.Column("ip", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
    if not _index_exists("user_sessions", "ix_user_sessions_user_id"):
        op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    if not _index_exists("user_sessions", "ix_user_sessions_expires_at"):
        op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"], unique=False)
    if not _index_exists("user_sessions", "ix_user_sessions_revoked_at"):
        op.create_index("ix_user_sessions_revoked_at", "user_sessions", ["revoked_at"], unique=False)

    if not _table_exists("invite_requests"):
        op.create_table(
            "invite_requests",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("email_normalized", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("requested_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("rejected_at", sa.DateTime(), nullable=True),
            sa.Column("approved_by_user_id", sa.String(length=36), nullable=True),
            sa.Column("invite_id", sa.String(length=36), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("captcha_verified_at", sa.DateTime(), nullable=True),
            sa.Column("ip", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["invite_id"], ["invite_codes.id"]),
        )
    if not _index_exists("invite_requests", "ix_invite_requests_email_normalized"):
        op.create_index("ix_invite_requests_email_normalized", "invite_requests", ["email_normalized"], unique=False)
    if not _index_exists("invite_requests", "ix_invite_requests_status"):
        op.create_index("ix_invite_requests_status", "invite_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_invite_requests_status", table_name="invite_requests")
    op.drop_index("ix_invite_requests_email_normalized", table_name="invite_requests")
    op.drop_table("invite_requests")

    op.drop_index("ix_user_sessions_revoked_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index("ix_invite_codes_revoked_at", table_name="invite_codes")
    op.drop_index("ix_invite_codes_expires_at", table_name="invite_codes")
    op.drop_constraint("uq_invite_codes_token_hash", "invite_codes", type_="unique")
    op.drop_index("ix_invite_codes_invite_email_normalized", table_name="invite_codes")
    op.drop_index("ix_invite_codes_invite_email", table_name="invite_codes")
    op.drop_column("invite_codes", "revoked_at")
    op.drop_column("invite_codes", "sent_at")
    op.drop_column("invite_codes", "expires_at")
    op.drop_column("invite_codes", "token_hash")
    op.drop_column("invite_codes", "invite_email_normalized")
    op.drop_column("invite_codes", "invite_email")

    op.drop_index("ix_users_expires_at", table_name="users")
    op.drop_constraint("uq_users_email_normalized", "users", type_="unique")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "suspended_reason")
    op.drop_column("users", "suspended_at")
    op.drop_column("users", "expires_at")
    op.drop_column("users", "email_normalized")

"""Add friendship table

Revision ID: a4f2c8d91b34
Revises: c7d8e9f0a1b2
Create Date: 2026-05-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a4f2c8d91b34"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "friendship",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("friend_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["friend_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "friend_id", name="friendship_user_friend_key"),
    )
    op.create_index("ix_friendship_friend_id", "friendship", ["friend_id"])
    op.create_index("ix_friendship_status", "friendship", ["status"])
    op.create_index("ix_friendship_user_id", "friendship", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_friendship_user_id", table_name="friendship")
    op.drop_index("ix_friendship_status", table_name="friendship")
    op.drop_index("ix_friendship_friend_id", table_name="friendship")
    op.drop_table("friendship")

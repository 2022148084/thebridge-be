"""Resize vector dimensions from 1536 to 768 (Gemini text-embedding-004)

Revision ID: b5e1f0a2c3d4
Revises: a4f2c8d91b34
Create Date: 2026-05-17 00:00:00.000000
"""

from alembic import op

revision = "b5e1f0a2c3d4"
down_revision = "a4f2c8d91b34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE user_preferences ALTER COLUMN core_embedding TYPE vector(768) USING NULL"
    )
    op.execute(
        "ALTER TABLE user_preferences ALTER COLUMN recent_embedding TYPE vector(768) USING NULL"
    )
    op.execute(
        "ALTER TABLE gathering ALTER COLUMN description_embedding TYPE vector(768) USING NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE user_preferences ALTER COLUMN core_embedding TYPE vector(1536) USING NULL"
    )
    op.execute(
        "ALTER TABLE user_preferences ALTER COLUMN recent_embedding TYPE vector(1536) USING NULL"
    )
    op.execute(
        "ALTER TABLE gathering ALTER COLUMN description_embedding TYPE vector(1536) USING NULL"
    )

"""Resize vector dimensions from 768 to 3072 (gemini-embedding-exp-03-07 default)

Revision ID: c6f2a1b3d4e5
Revises: b5e1f0a2c3d4
Create Date: 2026-05-17 00:00:00.000000
"""

from alembic import op

revision = "c6f2a1b3d4e5"
down_revision = "b5e1f0a2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE user_preferences ALTER COLUMN core_embedding TYPE vector(3072) USING NULL"
    )
    op.execute(
        "ALTER TABLE user_preferences ALTER COLUMN recent_embedding TYPE vector(3072) USING NULL"
    )
    op.execute(
        "ALTER TABLE gathering ALTER COLUMN description_embedding TYPE vector(3072) USING NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE user_preferences ALTER COLUMN core_embedding TYPE vector(768) USING NULL"
    )
    op.execute(
        "ALTER TABLE user_preferences ALTER COLUMN recent_embedding TYPE vector(768) USING NULL"
    )
    op.execute(
        "ALTER TABLE gathering ALTER COLUMN description_embedding TYPE vector(768) USING NULL"
    )

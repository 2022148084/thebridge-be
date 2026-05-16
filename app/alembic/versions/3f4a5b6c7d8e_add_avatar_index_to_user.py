"""Add avatar index to user

Revision ID: 3f4a5b6c7d8e
Revises: d7e8f9a0b1c2
Create Date: 2026-05-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3f4a5b6c7d8e"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("avatar_index", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "avatar_index")

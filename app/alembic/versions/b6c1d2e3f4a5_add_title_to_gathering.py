"""Add title to gathering

Revision ID: b6c1d2e3f4a5
Revises: a4f2c8d91b34
Create Date: 2026-05-17 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "b6c1d2e3f4a5"
down_revision = "a4f2c8d91b34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gathering",
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("gathering", "title", server_default=None)


def downgrade() -> None:
    op.drop_column("gathering", "title")

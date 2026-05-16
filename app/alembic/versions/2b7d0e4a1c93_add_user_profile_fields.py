"""Add user profile fields

Revision ID: 2b7d0e4a1c93
Revises: fe56fa70289e
Create Date: 2026-05-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b7d0e4a1c93"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("user", sa.Column("sex", sa.Integer(), nullable=True))
    op.add_column("user", sa.Column("city", sa.String(length=255), nullable=True))
    op.add_column(
        "user", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("user", "updated_at")
    op.drop_column("user", "city")
    op.drop_column("user", "sex")
    op.drop_column("user", "age")

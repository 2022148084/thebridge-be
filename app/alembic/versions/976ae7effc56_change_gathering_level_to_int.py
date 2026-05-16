"""Change gathering.level from varchar to integer

Revision ID: 976ae7effc56
Revises: 1cd924dd1b0d
Create Date: 2026-05-16 00:00:00.000000
"""

from alembic import op

revision = "976ae7effc56"
down_revision = "1cd924dd1b0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE gathering ALTER COLUMN level TYPE integer USING level::integer"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE gathering ALTER COLUMN level TYPE varchar(50) USING level::varchar"
    )

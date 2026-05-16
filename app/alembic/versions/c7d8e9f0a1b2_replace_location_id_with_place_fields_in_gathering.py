"""Replace location_id FK with place_name/city/lat/lng in gathering

Revision ID: c7d8e9f0a1b2
Revises: 976ae7effc56
Create Date: 2026-05-16 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "c7d8e9f0a1b2"
down_revision = "976ae7effc56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("gathering_location_id_fkey", "gathering", type_="foreignkey")
    op.drop_column("gathering", "location_id")

    op.add_column("gathering", sa.Column("place_name", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("gathering", sa.Column("city", sa.String(length=50), nullable=False, server_default=""))
    op.add_column("gathering", sa.Column("lat", sa.Float(), nullable=False, server_default="0"))
    op.add_column("gathering", sa.Column("lng", sa.Float(), nullable=False, server_default="0"))

    op.alter_column("gathering", "place_name", server_default=None)
    op.alter_column("gathering", "city", server_default=None)
    op.alter_column("gathering", "lat", server_default=None)
    op.alter_column("gathering", "lng", server_default=None)


def downgrade() -> None:
    op.drop_column("gathering", "lng")
    op.drop_column("gathering", "lat")
    op.drop_column("gathering", "city")
    op.drop_column("gathering", "place_name")

    op.add_column("gathering", sa.Column("location_id", sa.UUID(), nullable=False, server_default="00000000-0000-0000-0000-000000000000"))
    op.alter_column("gathering", "location_id", server_default=None)
    op.create_foreign_key(
        "gathering_location_id_fkey",
        "gathering",
        "location",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

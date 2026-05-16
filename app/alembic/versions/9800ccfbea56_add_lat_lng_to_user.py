"""add lat lng to user

Revision ID: 9800ccfbea56
Revises: d7e8f9a0b1c2
Create Date: 2026-05-16 21:36:32.740040

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '9800ccfbea56'
down_revision = '3f4a5b6c7d8e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('lat', sa.Float(), nullable=True))
    op.add_column('user', sa.Column('lng', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('user', 'lng')
    op.drop_column('user', 'lat')

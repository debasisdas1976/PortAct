"""Add xirr_manual column to assets table

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-03-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'i0j1k2l3m4n5'
down_revision = 'h9i0j1k2l3m4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('assets', sa.Column('xirr_manual', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('assets', 'xirr_manual')

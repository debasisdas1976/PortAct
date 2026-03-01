"""Add XIRR column to assets table

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-03-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h9i0j1k2l3m4'
down_revision = 'g8h9i0j1k2l3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('assets', sa.Column('xirr', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('assets', 'xirr')

"""add price update tracking to assets

Revision ID: add_price_update_tracking
Revises: d15e1bd9c188
Create Date: 2026-02-17 10:41:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_price_update_tracking'
down_revision = 'd15e1bd9c188'
branch_labels = None
depends_on = None


def upgrade():
    # Add price update tracking columns to assets table
    op.add_column('assets', sa.Column('price_update_failed', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('assets', sa.Column('last_price_update', sa.DateTime(timezone=True), nullable=True))
    op.add_column('assets', sa.Column('price_update_error', sa.Text(), nullable=True))


def downgrade():
    # Remove price update tracking columns
    op.drop_column('assets', 'price_update_error')
    op.drop_column('assets', 'last_price_update')
    op.drop_column('assets', 'price_update_failed')

# Made with Bob

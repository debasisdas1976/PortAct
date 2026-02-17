"""add_isin_field_to_assets

Revision ID: 966035a35932
Revises: add_api_symbol_field
Create Date: 2026-02-17 11:28:16.814652

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '966035a35932'
down_revision = 'add_api_symbol_field'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add isin column to assets table
    op.add_column('assets', sa.Column('isin', sa.String(), nullable=True))
    op.create_index(op.f('ix_assets_isin'), 'assets', ['isin'], unique=False)


def downgrade() -> None:
    # Remove isin column from assets table
    op.drop_index(op.f('ix_assets_isin'), table_name='assets')
    op.drop_column('assets', 'isin')
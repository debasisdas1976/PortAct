"""add api_symbol field to assets

Revision ID: add_api_symbol_field
Revises: add_price_update_tracking
Create Date: 2026-02-17 10:57:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_api_symbol_field'
down_revision = 'add_price_update_tracking'
branch_labels = None
depends_on = None


def upgrade():
    # Add api_symbol column to assets table
    op.add_column('assets', sa.Column('api_symbol', sa.String(), nullable=True))
    op.create_index(op.f('ix_assets_api_symbol'), 'assets', ['api_symbol'], unique=False)
    
    # Copy existing symbol values to api_symbol for backward compatibility
    op.execute('UPDATE assets SET api_symbol = symbol WHERE api_symbol IS NULL')


def downgrade():
    # Remove api_symbol column
    op.drop_index(op.f('ix_assets_api_symbol'), table_name='assets')
    op.drop_column('assets', 'api_symbol')

# Made with Bob

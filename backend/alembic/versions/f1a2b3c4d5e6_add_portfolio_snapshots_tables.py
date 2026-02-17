"""add_portfolio_snapshots_tables

Revision ID: f1a2b3c4d5e6
Revises: 68eca3fa4082
Create Date: 2026-02-17 19:47:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '68eca3fa4082'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create portfolio_snapshots table
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('total_invested', sa.Float(), nullable=True, default=0.0),
        sa.Column('total_current_value', sa.Float(), nullable=True, default=0.0),
        sa.Column('total_profit_loss', sa.Float(), nullable=True, default=0.0),
        sa.Column('total_profit_loss_percentage', sa.Float(), nullable=True, default=0.0),
        sa.Column('total_assets_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_snapshots_id'), 'portfolio_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_portfolio_snapshots_snapshot_date'), 'portfolio_snapshots', ['snapshot_date'], unique=False)
    op.create_index('idx_user_snapshot_date', 'portfolio_snapshots', ['user_id', 'snapshot_date'], unique=False)
    
    # Create asset_snapshots table
    op.create_table(
        'asset_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_snapshot_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('asset_type', sa.String(), nullable=False),
        sa.Column('asset_name', sa.String(), nullable=False),
        sa.Column('asset_symbol', sa.String(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True, default=0.0),
        sa.Column('purchase_price', sa.Float(), nullable=True, default=0.0),
        sa.Column('current_price', sa.Float(), nullable=True, default=0.0),
        sa.Column('total_invested', sa.Float(), nullable=True, default=0.0),
        sa.Column('current_value', sa.Float(), nullable=True, default=0.0),
        sa.Column('profit_loss', sa.Float(), nullable=True, default=0.0),
        sa.Column('profit_loss_percentage', sa.Float(), nullable=True, default=0.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_snapshot_id'], ['portfolio_snapshots.id'], ),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asset_snapshots_id'), 'asset_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_asset_snapshots_snapshot_date'), 'asset_snapshots', ['snapshot_date'], unique=False)
    op.create_index('idx_asset_snapshot_date', 'asset_snapshots', ['asset_id', 'snapshot_date'], unique=False)
    op.create_index('idx_portfolio_snapshot', 'asset_snapshots', ['portfolio_snapshot_id', 'snapshot_date'], unique=False)


def downgrade() -> None:
    # Drop asset_snapshots table
    op.drop_index('idx_portfolio_snapshot', table_name='asset_snapshots')
    op.drop_index('idx_asset_snapshot_date', table_name='asset_snapshots')
    op.drop_index(op.f('ix_asset_snapshots_snapshot_date'), table_name='asset_snapshots')
    op.drop_index(op.f('ix_asset_snapshots_id'), table_name='asset_snapshots')
    op.drop_table('asset_snapshots')
    
    # Drop portfolio_snapshots table
    op.drop_index('idx_user_snapshot_date', table_name='portfolio_snapshots')
    op.drop_index(op.f('ix_portfolio_snapshots_snapshot_date'), table_name='portfolio_snapshots')
    op.drop_index(op.f('ix_portfolio_snapshots_id'), table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')

# Made with Bob
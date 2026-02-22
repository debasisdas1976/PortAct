"""add_mutual_fund_holdings_table

Revision ID: 68eca3fa4082
Revises: e1f2a3b4c5d6
Create Date: 2026-02-17 13:34:30.300733

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '68eca3fa4082'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create mutual_fund_holdings table
    op.create_table(
        'mutual_fund_holdings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stock_name', sa.String(), nullable=False),
        sa.Column('stock_symbol', sa.String(), nullable=True),
        sa.Column('isin', sa.String(), nullable=True),
        sa.Column('holding_percentage', sa.Float(), nullable=False),
        sa.Column('holding_value', sa.Float(), nullable=True, server_default='0'),
        sa.Column('quantity_held', sa.Float(), nullable=True, server_default='0'),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('market_cap', sa.String(), nullable=True),
        sa.Column('stock_current_price', sa.Float(), nullable=True, server_default='0'),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_mutual_fund_holdings_id'), 'mutual_fund_holdings', ['id'], unique=False)
    op.create_index(op.f('ix_mutual_fund_holdings_asset_id'), 'mutual_fund_holdings', ['asset_id'], unique=False)
    op.create_index(op.f('ix_mutual_fund_holdings_user_id'), 'mutual_fund_holdings', ['user_id'], unique=False)
    op.create_index(op.f('ix_mutual_fund_holdings_stock_symbol'), 'mutual_fund_holdings', ['stock_symbol'], unique=False)
    op.create_index(op.f('ix_mutual_fund_holdings_isin'), 'mutual_fund_holdings', ['isin'], unique=False)

    # Also add index on crypto_accounts (was the only thing in the original migration)
    op.create_index(op.f('ix_crypto_accounts_id'), 'crypto_accounts', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crypto_accounts_id'), table_name='crypto_accounts')

    op.drop_index(op.f('ix_mutual_fund_holdings_isin'), table_name='mutual_fund_holdings')
    op.drop_index(op.f('ix_mutual_fund_holdings_stock_symbol'), table_name='mutual_fund_holdings')
    op.drop_index(op.f('ix_mutual_fund_holdings_user_id'), table_name='mutual_fund_holdings')
    op.drop_index(op.f('ix_mutual_fund_holdings_asset_id'), table_name='mutual_fund_holdings')
    op.drop_index(op.f('ix_mutual_fund_holdings_id'), table_name='mutual_fund_holdings')
    op.drop_table('mutual_fund_holdings')

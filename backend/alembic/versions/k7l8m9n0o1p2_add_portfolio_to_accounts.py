"""Add portfolio_id to bank_accounts and demat_accounts

Revision ID: k7l8m9n0o1p2
Revises: j6k7l8m9n0o1
Create Date: 2025-02-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'k7l8m9n0o1p2'
down_revision = 'j6k7l8m9n0o1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add portfolio_id to bank_accounts
    op.add_column('bank_accounts', sa.Column('portfolio_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_bank_accounts_portfolio_id',
        'bank_accounts', 'portfolios',
        ['portfolio_id'], ['id']
    )
    op.create_index('ix_bank_accounts_portfolio_id', 'bank_accounts', ['portfolio_id'])

    # Add portfolio_id to demat_accounts
    op.add_column('demat_accounts', sa.Column('portfolio_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_demat_accounts_portfolio_id',
        'demat_accounts', 'portfolios',
        ['portfolio_id'], ['id']
    )
    op.create_index('ix_demat_accounts_portfolio_id', 'demat_accounts', ['portfolio_id'])


def downgrade() -> None:
    op.drop_index('ix_demat_accounts_portfolio_id', table_name='demat_accounts')
    op.drop_constraint('fk_demat_accounts_portfolio_id', 'demat_accounts', type_='foreignkey')
    op.drop_column('demat_accounts', 'portfolio_id')

    op.drop_index('ix_bank_accounts_portfolio_id', table_name='bank_accounts')
    op.drop_constraint('fk_bank_accounts_portfolio_id', 'bank_accounts', type_='foreignkey')
    op.drop_column('bank_accounts', 'portfolio_id')

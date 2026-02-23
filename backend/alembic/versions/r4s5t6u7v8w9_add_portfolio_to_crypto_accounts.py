"""Add portfolio_id to crypto_accounts

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-02-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'r4s5t6u7v8w9'
down_revision = 'q3r4s5t6u7v8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add portfolio_id to crypto_accounts (matching bank_accounts and demat_accounts)
    op.add_column('crypto_accounts', sa.Column('portfolio_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_crypto_accounts_portfolio_id',
        'crypto_accounts', 'portfolios',
        ['portfolio_id'], ['id']
    )
    op.create_index('ix_crypto_accounts_portfolio_id', 'crypto_accounts', ['portfolio_id'])


def downgrade() -> None:
    op.drop_index('ix_crypto_accounts_portfolio_id', table_name='crypto_accounts')
    op.drop_constraint('fk_crypto_accounts_portfolio_id', 'crypto_accounts', type_='foreignkey')
    op.drop_column('crypto_accounts', 'portfolio_id')

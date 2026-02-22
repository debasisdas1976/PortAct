"""Add portfolio_id to expenses

Revision ID: l8m9n0o1p2q3
Revises: k7l8m9n0o1p2
Create Date: 2025-02-21 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'l8m9n0o1p2q3'
down_revision = 'k7l8m9n0o1p2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add portfolio_id to expenses
    op.add_column('expenses', sa.Column('portfolio_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_expenses_portfolio_id',
        'expenses', 'portfolios',
        ['portfolio_id'], ['id']
    )
    op.create_index('ix_expenses_portfolio_id', 'expenses', ['portfolio_id'])


def downgrade() -> None:
    op.drop_index('ix_expenses_portfolio_id', table_name='expenses')
    op.drop_constraint('fk_expenses_portfolio_id', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'portfolio_id')

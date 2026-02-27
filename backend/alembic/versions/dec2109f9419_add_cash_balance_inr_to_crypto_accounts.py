"""Add cash_balance_inr to crypto_accounts

Revision ID: dec2109f9419
Revises: fc01d2e3f4a5
Create Date: 2026-02-27 11:44:35.865137

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dec2109f9419'
down_revision = 'fc01d2e3f4a5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('crypto_accounts', sa.Column('cash_balance_inr', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('crypto_accounts', 'cash_balance_inr')

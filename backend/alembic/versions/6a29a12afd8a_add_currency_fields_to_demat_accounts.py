"""add_currency_fields_to_demat_accounts

Revision ID: 6a29a12afd8a
Revises: 638328b96730
Create Date: 2026-02-15 14:03:43.141158

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a29a12afd8a'
down_revision = '638328b96730'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add currency and cash_balance_usd columns to demat_accounts table
    op.add_column('demat_accounts', sa.Column('currency', sa.String(), nullable=True))
    op.add_column('demat_accounts', sa.Column('cash_balance_usd', sa.Float(), nullable=True))
    
    # Set default currency to INR for existing accounts
    op.execute("UPDATE demat_accounts SET currency = 'INR' WHERE currency IS NULL")
    
    # Set currency to USD for Vested and INDMoney accounts (using CAST to compare enum values)
    op.execute("UPDATE demat_accounts SET currency = 'USD' WHERE broker_name::text IN ('vested', 'indmoney')")


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('demat_accounts', 'cash_balance_usd')
    op.drop_column('demat_accounts', 'currency')
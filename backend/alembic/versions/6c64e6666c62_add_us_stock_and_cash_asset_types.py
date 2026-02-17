"""add_us_stock_and_cash_asset_types

Revision ID: 6c64e6666c62
Revises: d99485f0973a
Create Date: 2026-02-14 19:01:02.815881

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6c64e6666c62'
down_revision = 'd99485f0973a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new asset types to the enum
    # PostgreSQL requires explicit enum modification
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'us_stock'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'cash'")
    
    # Add new statement types to the enum
    op.execute("ALTER TYPE statementtype ADD VALUE IF NOT EXISTS 'vested_statement'")
    op.execute("ALTER TYPE statementtype ADD VALUE IF NOT EXISTS 'indmoney_statement'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the values in place
    pass

# Made with Bob

"""split_mutual_fund_into_equity_and_debt

Revision ID: 2cf4fd9e4b0e
Revises: a56db82590f8
Create Date: 2026-02-13 14:19:10.355869

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2cf4fd9e4b0e'
down_revision = 'a56db82590f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ADD VALUE cannot use the new value in the same transaction on
    # PostgreSQL.  The recommended alembic pattern is: COMMIT the current
    # transaction, add the enum values outside any transaction, then BEGIN a
    # new transaction so the remaining DDL/DML (and alembic's version-table
    # update) lands in a fresh transaction that can reference the new values.
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'EQUITY_MUTUAL_FUND'"))
    op.execute(sa.text("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'DEBT_MUTUAL_FUND'"))
    op.execute(sa.text("BEGIN"))

    # Now convert existing MUTUAL_FUND assets to EQUITY_MUTUAL_FUND (default)
    op.execute("""
        UPDATE assets
        SET asset_type = 'EQUITY_MUTUAL_FUND'::assettype
        WHERE asset_type = 'MUTUAL_FUND'::assettype
    """)


def downgrade() -> None:
    # Revert EQUITY_MUTUAL_FUND and DEBT_MUTUAL_FUND back to MUTUAL_FUND
    op.execute("""
        UPDATE assets
        SET asset_type = 'MUTUAL_FUND'::assettype
        WHERE asset_type IN ('EQUITY_MUTUAL_FUND'::assettype, 'DEBT_MUTUAL_FUND'::assettype)
    """)

    # Note: Cannot remove enum values in PostgreSQL without recreating the enum
    # The old MUTUAL_FUND value will remain in the enum

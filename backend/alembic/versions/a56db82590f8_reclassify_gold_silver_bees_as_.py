"""reclassify_gold_silver_bees_as_commodities

Revision ID: a56db82590f8
Revises: 657cf303af8e
Create Date: 2026-02-13 13:59:52.214558

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a56db82590f8'
down_revision = '657cf303af8e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update existing SILVERBEES and GOLDBEES records to commodity type
    op.execute("""
        UPDATE assets
        SET asset_type = 'COMMODITY'::assettype
        WHERE UPPER(symbol) IN ('SILVERBEES', 'GOLDBEES', 'GOLDSHARE', 'SILVERSHARE')
        AND asset_type != 'COMMODITY'::assettype
    """)


def downgrade() -> None:
    # Revert SILVERBEES and GOLDBEES back to mutual_fund type
    op.execute("""
        UPDATE assets
        SET asset_type = 'MUTUAL_FUND'::assettype
        WHERE UPPER(symbol) IN ('SILVERBEES', 'GOLDBEES', 'GOLDSHARE', 'SILVERSHARE')
        AND asset_type = 'COMMODITY'::assettype
    """)
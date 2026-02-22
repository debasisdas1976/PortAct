"""Add Debt Mutual Fund category and reassign debt_mutual_fund asset type

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-02-22

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'q3r4s5t6u7v8'
down_revision = 'p2q3r4s5t6u7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE asset_types
        SET category = 'Debt Mutual Fund'
        WHERE name = 'debt_mutual_fund';
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE asset_types
        SET category = 'Fixed Income'
        WHERE name = 'debt_mutual_fund';
    """)

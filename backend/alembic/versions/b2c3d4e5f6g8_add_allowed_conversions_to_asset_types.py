"""Add allowed_conversions column to asset_types table

Stores a JSON list of asset type names that each type can be converted to.
Types with null/empty allowed_conversions cannot be changed.

Revision ID: b2c3d4e5f6g8
Revises: a1b2c3d4e5f7
Create Date: 2026-02-26
"""
import json
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6g8'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None

# Allowed conversions data
CONVERSIONS = {
    "stock": ["us_stock", "reit", "invit", "esop", "rsu", "commodity"],
    "us_stock": ["stock", "esop", "rsu"],
    "reit": ["stock", "invit"],
    "invit": ["stock", "reit"],
    "sovereign_gold_bond": ["stock"],
    "esop": ["rsu", "stock", "us_stock"],
    "rsu": ["esop", "stock", "us_stock"],
    "equity_mutual_fund": ["hybrid_mutual_fund", "debt_mutual_fund", "commodity"],
    "hybrid_mutual_fund": ["equity_mutual_fund", "debt_mutual_fund", "commodity"],
    "debt_mutual_fund": ["equity_mutual_fund", "hybrid_mutual_fund", "commodity"],
    "commodity": ["stock", "equity_mutual_fund", "hybrid_mutual_fund", "debt_mutual_fund"],
    "fixed_deposit": ["recurring_deposit"],
    "recurring_deposit": ["fixed_deposit"],
    "corporate_bond": ["rbi_bond", "tax_saving_bond"],
    "rbi_bond": ["corporate_bond", "tax_saving_bond"],
    "tax_saving_bond": ["corporate_bond", "rbi_bond"],
    "nsc": ["kvp"],
    "kvp": ["nsc"],
    "scss": ["mis"],
    "mis": ["scss"],
}


def upgrade() -> None:
    op.add_column('asset_types', sa.Column('allowed_conversions', sa.JSON(), nullable=True))

    for name, conversions in CONVERSIONS.items():
        op.execute(
            sa.text(
                "UPDATE asset_types SET allowed_conversions = :conv WHERE name = :name"
            ).bindparams(conv=json.dumps(conversions), name=name)
        )


def downgrade() -> None:
    op.drop_column('asset_types', 'allowed_conversions')

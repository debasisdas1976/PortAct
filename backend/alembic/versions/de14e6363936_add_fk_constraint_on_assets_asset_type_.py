"""Add FK constraint on assets.asset_type to asset_types.name

Converts assets.asset_type from PG native enum (assettype) to VARCHAR(50)
so it can have a foreign key to asset_types.name. The LowerEnumStr
TypeDecorator in Python still maps between VARCHAR and the AssetType enum,
so all application code continues to work unchanged.

Revision ID: de14e6363936
Revises: b2c3d4e5f6g8
Create Date: 2026-02-26 19:16:55.593619

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'de14e6363936'
down_revision = 'b2c3d4e5f6g8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Convert assets.asset_type from PG enum 'assettype' to VARCHAR(50)
    op.execute(
        "ALTER TABLE assets ALTER COLUMN asset_type "
        "TYPE VARCHAR(50) USING asset_type::text"
    )

    # Step 2: Drop the now-unused assettype enum type
    op.execute("DROP TYPE IF EXISTS assettype")

    # Step 3: Add FK constraint to asset_types.name
    op.create_foreign_key(
        'fk_assets_asset_type_asset_types',
        'assets', 'asset_types',
        ['asset_type'], ['name'],
    )


def downgrade() -> None:
    # Step 1: Drop the FK constraint
    op.drop_constraint('fk_assets_asset_type_asset_types', 'assets', type_='foreignkey')

    # Step 2: Recreate the assettype PG enum with lowercase labels
    labels = [
        "stock", "us_stock", "equity_mutual_fund", "hybrid_mutual_fund",
        "debt_mutual_fund", "commodity", "crypto", "savings_account",
        "recurring_deposit", "fixed_deposit", "real_estate", "ppf", "pf",
        "nps", "ssy", "insurance_policy", "gratuity", "cash", "nsc",
        "kvp", "scss", "mis", "corporate_bond", "rbi_bond",
        "tax_saving_bond", "reit", "invit", "sovereign_gold_bond",
        "esop", "rsu",
    ]
    labels_sql = ", ".join(f"'{label}'" for label in labels)
    op.execute(f"CREATE TYPE assettype AS ENUM ({labels_sql})")

    # Step 3: Convert column back to PG enum
    op.execute(
        "ALTER TABLE assets ALTER COLUMN asset_type "
        "TYPE assettype USING asset_type::assettype"
    )

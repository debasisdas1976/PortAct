"""add_new_asset_types

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add enum values (lowercase) matching Python enum .value
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'nsc'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'kvp'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'scss'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'mis'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'corporate_bond'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'rbi_bond'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'tax_saving_bond'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'reit'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'invit'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'sovereign_gold_bond'")
    # Add enum names (uppercase) — SQLAlchemy Enum() stores Python enum .name by default
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'NSC'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'KVP'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'SCSS'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'MIS'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'CORPORATE_BOND'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'RBI_BOND'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'TAX_SAVING_BOND'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'REIT'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'INVIT'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'SOVEREIGN_GOLD_BOND'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type
    pass

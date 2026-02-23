"""add_missing_uppercase_enum_values

Revision ID: w9x0y1z2a3b4
Revises: v8w9x0y1z2a3
Create Date: 2026-02-23 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'w9x0y1z2a3b4'
down_revision = 'v8w9x0y1z2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These asset types were added in lowercase only, but SQLAlchemy's
    # Enum(AssetType) stores the Python enum .name (UPPERCASE) by default.
    # Add the missing uppercase variants so inserts don't fail.
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'GRATUITY'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'US_STOCK'")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'CASH'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type
    pass

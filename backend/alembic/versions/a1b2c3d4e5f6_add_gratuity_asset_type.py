"""add_gratuity_asset_type

Revision ID: a1b2c3d4e5f6
Revises: 27ce3b2882b3
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '27ce3b2882b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'gratuity'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type
    pass

"""make_asset_id_nullable_in_asset_snapshots

Revision ID: 27ce3b2882b3
Revises: f1a2b3c4d5e6
Create Date: 2026-02-17 20:26:26.788610

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '27ce3b2882b3'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make asset_id nullable to support bank accounts in snapshots
    op.alter_column('asset_snapshots', 'asset_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)


def downgrade() -> None:
    # Revert asset_id to not nullable
    op.alter_column('asset_snapshots', 'asset_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
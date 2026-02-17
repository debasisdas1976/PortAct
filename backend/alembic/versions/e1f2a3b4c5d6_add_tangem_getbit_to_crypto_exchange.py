"""add_tangem_getbit_to_crypto_exchange

Revision ID: e1f2a3b4c5d6
Revises: d15e1bd9c188
Create Date: 2026-02-17 13:12:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = '966035a35932'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new values to the cryptoexchange enum
    op.execute("ALTER TYPE cryptoexchange ADD VALUE IF NOT EXISTS 'tangem'")
    op.execute("ALTER TYPE cryptoexchange ADD VALUE IF NOT EXISTS 'getbit'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type and updating all references
    # For simplicity, we'll leave the enum values in place on downgrade
    pass

# Made with Bob

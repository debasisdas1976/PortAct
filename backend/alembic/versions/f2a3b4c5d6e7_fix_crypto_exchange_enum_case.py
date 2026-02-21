"""fix_crypto_exchange_enum_case

Revision ID: f2a3b4c5d6e7
Revises: e5f6g7h8i9j0
Create Date: 2026-02-21 12:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f2a3b4c5d6e7'
down_revision = 'e5f6g7h8i9j0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The 'tangem' and 'getbit' values were added in lowercase,
    # but SQLAlchemy stores enum member NAMES (uppercase).
    # Rename them to uppercase to match all other values.
    op.execute("ALTER TYPE cryptoexchange RENAME VALUE 'tangem' TO 'TANGEM'")
    op.execute("ALTER TYPE cryptoexchange RENAME VALUE 'getbit' TO 'GETBIT'")


def downgrade() -> None:
    op.execute("ALTER TYPE cryptoexchange RENAME VALUE 'TANGEM' TO 'tangem'")
    op.execute("ALTER TYPE cryptoexchange RENAME VALUE 'GETBIT' TO 'getbit'")

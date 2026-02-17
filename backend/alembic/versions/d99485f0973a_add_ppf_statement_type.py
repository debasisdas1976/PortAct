"""add_ppf_statement_type

Revision ID: d99485f0973a
Revises: cf70a5dc799b
Create Date: 2026-02-14 14:57:03.541395

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd99485f0973a'
down_revision = 'cf70a5dc799b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add PPF_STATEMENT to the statementtype enum
    op.execute("ALTER TYPE statementtype ADD VALUE IF NOT EXISTS 'PPF_STATEMENT'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # You would need to recreate the enum type if you want to remove the value
    pass
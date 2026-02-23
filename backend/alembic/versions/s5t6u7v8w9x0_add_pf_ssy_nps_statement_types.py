"""Add PF, SSY, NPS statement types to statementtype enum

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-02-23 12:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 's5t6u7v8w9x0'
down_revision = 'r4s5t6u7v8w9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE statementtype ADD VALUE IF NOT EXISTS 'PF_STATEMENT'")
    op.execute("ALTER TYPE statementtype ADD VALUE IF NOT EXISTS 'SSY_STATEMENT'")
    op.execute("ALTER TYPE statementtype ADD VALUE IF NOT EXISTS 'NPS_STATEMENT'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type
    pass

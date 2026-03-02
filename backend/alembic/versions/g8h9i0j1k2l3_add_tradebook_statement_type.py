"""Add tradebook_statement type to statementtype enum

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2026-02-27

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'g8h9i0j1k2l3'
down_revision = 'f7g8h9i0j1k2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE statementtype ADD VALUE IF NOT EXISTS 'tradebook_statement';")


def downgrade() -> None:
    pass

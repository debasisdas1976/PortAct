"""add user preferences column

Revision ID: s6t7u8v9w0x1
Revises: z2a3b4c5d6e7
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "s6t7u8v9w0x1"
down_revision = "r5s6t7u8v9w0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preferences", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preferences")

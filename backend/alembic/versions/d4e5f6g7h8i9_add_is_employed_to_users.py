"""Add is_employed column to users table

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'd4e5f6g7h8i9'
down_revision = 'c3d4e5f6g7h8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_employed', sa.Boolean(), nullable=True, server_default='true'))


def downgrade() -> None:
    op.drop_column('users', 'is_employed')

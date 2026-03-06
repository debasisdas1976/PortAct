"""Rename asset_attributes.color to icon

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'k2l3m4n5o6p7'
down_revision = 'j1k2l3m4n5o6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('asset_attributes', 'color', new_column_name='icon', type_=sa.String(50))


def downgrade() -> None:
    op.alter_column('asset_attributes', 'icon', new_column_name='color', type_=sa.String(20))

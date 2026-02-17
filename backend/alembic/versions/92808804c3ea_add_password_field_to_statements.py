"""add_password_field_to_statements

Revision ID: 92808804c3ea
Revises: 2cf4fd9e4b0e
Create Date: 2026-02-13 15:02:52.779142

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '92808804c3ea'
down_revision = '2cf4fd9e4b0e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password column to statements table
    op.add_column('statements', sa.Column('password', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove password column from statements table
    op.drop_column('statements', 'password')
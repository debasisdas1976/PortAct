"""merge nse_holidays into main branch

Revision ID: f29c6802b2a8
Revises: a3b4c5d6e7f8, m4n5o6p7q8r9
Create Date: 2026-03-12 10:50:50.599557

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f29c6802b2a8'
down_revision = ('a3b4c5d6e7f8', 'm4n5o6p7q8r9')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
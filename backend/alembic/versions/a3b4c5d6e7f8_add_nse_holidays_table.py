"""Add nse_holidays table for NSE trading holiday calendar.

Populated once per year by the scheduler (on startup if missing,
and annually on Dec 1 to seed the coming year's holiday list).

Revision ID: a3b4c5d6e7f8
Revises: z2a3b4c5d6e7
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa

revision = 'a3b4c5d6e7f8'
down_revision = 'z2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'nse_holidays',
        sa.Column('id',   sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date(),         nullable=False),
        sa.Column('name', sa.String(200),    nullable=False),
        sa.Column('year', sa.Integer(),      nullable=False),
    )
    op.create_index('ix_nse_holidays_date', 'nse_holidays', ['date'], unique=True)
    op.create_index('ix_nse_holidays_year', 'nse_holidays', ['year'], unique=False)


def downgrade():
    op.drop_index('ix_nse_holidays_year', table_name='nse_holidays')
    op.drop_index('ix_nse_holidays_date', table_name='nse_holidays')
    op.drop_table('nse_holidays')

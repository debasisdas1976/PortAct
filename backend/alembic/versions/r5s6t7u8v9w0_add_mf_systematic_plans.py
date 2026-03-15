"""Add mf_systematic_plans table for SIP/STP/SWP schedules.

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'r5s6t7u8v9w0'
down_revision = 'q4r5s6t7u8v9'
branch_labels = None
depends_on = None

# Pre-create enum types so they exist before the table references them
_plan_type_enum = postgresql.ENUM('sip', 'stp', 'swp', name='systematicplantype', create_type=False)
_frequency_enum = postgresql.ENUM('daily', 'weekly', 'fortnightly', 'monthly', name='systematicfrequency', create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    # Create enum types if not already present
    bind.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE systematicplantype AS ENUM ('sip', 'stp', 'swp'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    ))
    bind.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE systematicfrequency AS ENUM ('daily', 'weekly', 'fortnightly', 'monthly'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    ))

    op.create_table(
        'mf_systematic_plans',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('plan_type', _plan_type_enum, nullable=False, index=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('frequency', _frequency_enum, nullable=False),
        sa.Column('execution_day', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_executed_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('mf_systematic_plans')
    op.execute("DROP TYPE IF EXISTS systematicplantype")
    op.execute("DROP TYPE IF EXISTS systematicfrequency")

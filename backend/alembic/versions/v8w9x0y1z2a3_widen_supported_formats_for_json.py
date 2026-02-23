"""Widen supported_formats column to hold per-account-type JSON

Revision ID: v8w9x0y1z2a3
Revises: u7v8w9x0y1z2
Create Date: 2026-02-23 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'v8w9x0y1z2a3'
down_revision = 'u7v8w9x0y1z2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Increase supported_formats from VARCHAR(100) to VARCHAR(500)
    # to accommodate per-account-type JSON config for banks
    with op.batch_alter_table('banks') as batch_op:
        batch_op.alter_column(
            'supported_formats',
            existing_type=sa.String(100),
            type_=sa.String(500),
            existing_nullable=True,
        )

    with op.batch_alter_table('brokers') as batch_op:
        batch_op.alter_column(
            'supported_formats',
            existing_type=sa.String(100),
            type_=sa.String(500),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('brokers') as batch_op:
        batch_op.alter_column(
            'supported_formats',
            existing_type=sa.String(500),
            type_=sa.String(100),
            existing_nullable=True,
        )

    with op.batch_alter_table('banks') as batch_op:
        batch_op.alter_column(
            'supported_formats',
            existing_type=sa.String(500),
            type_=sa.String(100),
            existing_nullable=True,
        )

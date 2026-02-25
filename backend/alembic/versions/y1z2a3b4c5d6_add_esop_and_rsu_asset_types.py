"""Add ESOP and RSU asset types

Revision ID: y1z2a3b4c5d6
Revises: x0y1z2a3b4c5
Create Date: 2026-02-25

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'y1z2a3b4c5d6'
down_revision = 'x0y1z2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'ESOP';")
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'RSU';")
    op.execute("""
        INSERT INTO asset_types (name, display_label, category, is_active, sort_order)
        VALUES ('esop', 'ESOP', 'Equity', TRUE, 7)
        ON CONFLICT (name) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO asset_types (name, display_label, category, is_active, sort_order)
        VALUES ('rsu', 'RSU', 'Equity', TRUE, 8)
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM asset_types WHERE name = 'esop';")
    op.execute("DELETE FROM asset_types WHERE name = 'rsu';")

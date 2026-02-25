"""Add hybrid_mutual_fund asset type

Revision ID: x0y1z2a3b4c5
Revises: w9x0y1z2a3b4
Create Date: 2026-02-25

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'x0y1z2a3b4c5'
down_revision = 'w9x0y1z2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'HYBRID_MUTUAL_FUND';")
    op.execute("""
        INSERT INTO asset_types (name, display_label, category, is_active, sort_order)
        VALUES ('hybrid_mutual_fund', 'Hybrid Mutual Fund', 'Hybrid', TRUE, 4)
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM asset_types WHERE name = 'hybrid_mutual_fund';
    """)

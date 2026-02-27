"""Add asset_categories table and FK from asset_types.category

Revision ID: f7g8h9i0j1k2
Revises: 845db891ca61
Create Date: 2026-02-27 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7g8h9i0j1k2'
down_revision: Union[str, None] = '845db891ca61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The 9 categories currently in use
CATEGORIES = [
    {"name": "Equity", "display_label": "Equity", "color": "#1976d2", "sort_order": 1},
    {"name": "Hybrid", "display_label": "Hybrid", "color": "#5c6bc0", "sort_order": 2},
    {"name": "Fixed Income", "display_label": "Fixed Income", "color": "#0097a7", "sort_order": 3},
    {"name": "Govt. Schemes", "display_label": "Govt. Schemes", "color": "#388e3c", "sort_order": 4},
    {"name": "Commodities", "display_label": "Commodities", "color": "#f57c00", "sort_order": 5},
    {"name": "Crypto", "display_label": "Crypto", "color": "#7b1fa2", "sort_order": 6},
    {"name": "Real Estate", "display_label": "Real Estate", "color": "#d32f2f", "sort_order": 7},
    {"name": "Cash", "display_label": "Cash", "color": "#26a69a", "sort_order": 8},
    {"name": "Other", "display_label": "Other", "color": "#757575", "sort_order": 9},
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create asset_categories table (idempotent — may already exist via create_all)
    table_exists = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'asset_categories')"
    )).scalar()

    if not table_exists:
        op.create_table(
            'asset_categories',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('display_label', sa.String(length=100), nullable=False),
            sa.Column('color', sa.String(length=7), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
            sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_asset_categories_id'), 'asset_categories', ['id'], unique=False)
        op.create_index(op.f('ix_asset_categories_name'), 'asset_categories', ['name'], unique=True)

    # 2. Seed categories (only rows that don't already exist)
    for cat in CATEGORIES:
        exists = conn.execute(sa.text(
            "SELECT 1 FROM asset_categories WHERE name = :name"
        ), {"name": cat["name"]}).scalar()
        if not exists:
            conn.execute(sa.text(
                "INSERT INTO asset_categories (name, display_label, color, sort_order, is_active) "
                "VALUES (:name, :display_label, :color, :sort_order, true)"
            ), cat)

    # 3. Add FK constraint (only if it doesn't already exist)
    fk_exists = conn.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'fk_asset_types_category_asset_categories'"
    )).scalar()
    if not fk_exists:
        op.create_foreign_key(
            'fk_asset_types_category_asset_categories',
            'asset_types', 'asset_categories',
            ['category'], ['name'],
        )


def downgrade() -> None:
    # 1. Drop FK constraint
    op.drop_constraint('fk_asset_types_category_asset_categories', 'asset_types', type_='foreignkey')

    # 2. Drop asset_categories table
    op.drop_index(op.f('ix_asset_categories_name'), table_name='asset_categories')
    op.drop_index(op.f('ix_asset_categories_id'), table_name='asset_categories')
    op.drop_table('asset_categories')

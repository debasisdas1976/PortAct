"""Seed india_gdp_growth historical data into macro_data_points.

Values are India annual real GDP growth % (World Bank NY.GDP.MKTP.KD.ZG).
World Bank calendar year X → India FY(X+1) (Apr X – Mar X+1).
Stored as period 'YYYY-03' (fiscal year-end March) with label 'FYXX'.
Seeded through FY25 (2024 calendar year); live scheduler fills subsequent years.

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'q4r5s6t7u8v9'
down_revision = 'p3q4r5s6t7u8'
branch_labels = None
depends_on = None

# Source: World Bank NY.GDP.MKTP.KD.ZG — India annual GDP growth %
# Calendar year X → India Fiscal Year X+1 (Apr X – Mar X+1)
# period = 'YYYY-03' (FY end), label = 'FYXX'
_SEED_ROWS = [
    ('india_gdp_growth', '2017-03', 'FY17',  8.3),
    ('india_gdp_growth', '2018-03', 'FY18',  6.8),
    ('india_gdp_growth', '2019-03', 'FY19',  6.5),
    ('india_gdp_growth', '2020-03', 'FY20',  4.0),
    ('india_gdp_growth', '2021-03', 'FY21', -5.8),
    ('india_gdp_growth', '2022-03', 'FY22',  9.1),
    ('india_gdp_growth', '2023-03', 'FY23',  7.2),
    ('india_gdp_growth', '2024-03', 'FY24',  8.2),
    ('india_gdp_growth', '2025-03', 'FY25',  6.5),  # World Bank calendar 2024 data
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO macro_data_points (series, period, label, value) "
            "VALUES (:series, :period, :label, :value) "
            "ON CONFLICT (series, period) DO NOTHING"
        ),
        [
            {"series": s, "period": p, "label": lbl, "value": v}
            for s, p, lbl, v in _SEED_ROWS
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM macro_data_points WHERE series = 'india_gdp_growth'"
        )
    )

"""Seed india_sip_inflow historical data into macro_data_points.

Values are monthly total SIP contributions in ₹ crore.
Source: AMFI monthly industry reports (portal.amfiindia.com).
Seeded through Feb 2026; the daily scheduler fills subsequent months from live AMFI XLS.

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'p3q4r5s6t7u8'
down_revision = 'o2p3q4r5s6t7'
branch_labels = None
depends_on = None

# Historical seed data: (series, period, label, value)
# Source: AMFI monthly industry reports — portal.amfiindia.com
# Values are total SIP contributions in ₹ crore for each month.
# Seeded through Feb 2026; live scheduler handles subsequent months.
_SEED_ROWS = [
    ('india_sip_inflow', '2023-01', "Jan'23", 13856.0),
    ('india_sip_inflow', '2023-02', "Feb'23", 13686.0),
    ('india_sip_inflow', '2023-03', "Mar'23", 14276.0),
    ('india_sip_inflow', '2023-04', "Apr'23", 14749.0),
    ('india_sip_inflow', '2023-05', "May'23", 14749.0),
    ('india_sip_inflow', '2023-06', "Jun'23", 14734.0),
    ('india_sip_inflow', '2023-07', "Jul'23", 15245.0),
    ('india_sip_inflow', '2023-08', "Aug'23", 15814.0),
    ('india_sip_inflow', '2023-09', "Sep'23", 16042.0),
    ('india_sip_inflow', '2023-10', "Oct'23", 16928.0),
    ('india_sip_inflow', '2023-11', "Nov'23", 17073.0),
    ('india_sip_inflow', '2023-12', "Dec'23", 17610.0),
    ('india_sip_inflow', '2024-01', "Jan'24", 18838.0),
    ('india_sip_inflow', '2024-02', "Feb'24", 19187.0),
    ('india_sip_inflow', '2024-03', "Mar'24", 19271.0),
    ('india_sip_inflow', '2024-04', "Apr'24", 20371.0),
    ('india_sip_inflow', '2024-05', "May'24", 20904.0),
    ('india_sip_inflow', '2024-06', "Jun'24", 21262.0),
    ('india_sip_inflow', '2024-07', "Jul'24", 23332.0),
    ('india_sip_inflow', '2024-08', "Aug'24", 23547.0),
    ('india_sip_inflow', '2024-09', "Sep'24", 24509.0),
    ('india_sip_inflow', '2024-10', "Oct'24", 25323.0),
    ('india_sip_inflow', '2024-11', "Nov'24", 25320.0),
    ('india_sip_inflow', '2024-12', "Dec'24", 26459.0),
    ('india_sip_inflow', '2025-01', "Jan'25", 26400.0),
    ('india_sip_inflow', '2025-02', "Feb'25", 25999.0),
    ('india_sip_inflow', '2025-03', "Mar'25", 26459.0),
    ('india_sip_inflow', '2025-04', "Apr'25", 26632.0),
    ('india_sip_inflow', '2025-05', "May'25", 26688.0),
    ('india_sip_inflow', '2025-06', "Jun'25", 26688.0),
    ('india_sip_inflow', '2025-07', "Jul'25", 27269.0),
    ('india_sip_inflow', '2025-08', "Aug'25", 28463.0),
    ('india_sip_inflow', '2025-09', "Sep'25", 29361.0),
    ('india_sip_inflow', '2025-10', "Oct'25", 28999.0),
    ('india_sip_inflow', '2025-11', "Nov'25", 29445.0),
    ('india_sip_inflow', '2025-12', "Dec'25", 31002.0),
    ('india_sip_inflow', '2026-01', "Jan'26", 31002.0),
    ('india_sip_inflow', '2026-02', "Feb'26", 29845.0),
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
            "DELETE FROM macro_data_points WHERE series = 'india_sip_inflow'"
        )
    )

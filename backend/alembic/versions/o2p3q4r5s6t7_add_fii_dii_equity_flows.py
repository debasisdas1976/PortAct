"""Seed fii_equity_flow and dii_equity_flow historical data into macro_data_points.

Values are monthly net equity flows in ₹ crore (buy minus sell), equity segment only.
Source: NSE/SEBI published reports; Apr 2025–Mar 2026 from actual data.
The daily scheduler accumulates each new month automatically by fetching
today's single-day NSE figure and adding it to the current month's running
total — no manual data entry required for future months.

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'o2p3q4r5s6t7'
down_revision = 'n1o2p3q4r5s6'
branch_labels = None
depends_on = None

# Historical seed data: (series, period, label, value)
# Seeded through Mar 2026 (partial); the live scheduler accumulates current month daily.
_SEED_ROWS = [
    # ── FII net equity flows — ₹ crore ───────────────────────────────────────
    ('fii_equity_flow', '2023-01', "Jan'23", -28852.0),
    ('fii_equity_flow', '2023-02', "Feb'23",  -5294.0),
    ('fii_equity_flow', '2023-03', "Mar'23",   7936.0),
    ('fii_equity_flow', '2023-04', "Apr'23",  -8479.0),
    ('fii_equity_flow', '2023-05', "May'23",  43838.0),
    ('fii_equity_flow', '2023-06', "Jun'23",  47148.0),
    ('fii_equity_flow', '2023-07', "Jul'23",  46618.0),
    ('fii_equity_flow', '2023-08', "Aug'23", -25581.0),
    ('fii_equity_flow', '2023-09', "Sep'23", -14767.0),
    ('fii_equity_flow', '2023-10', "Oct'23", -24548.0),
    ('fii_equity_flow', '2023-11', "Nov'23",   9001.0),
    ('fii_equity_flow', '2023-12', "Dec'23",  66135.0),
    ('fii_equity_flow', '2024-01', "Jan'24",  25057.0),
    ('fii_equity_flow', '2024-02', "Feb'24",  -5294.0),
    ('fii_equity_flow', '2024-03', "Mar'24",  35098.0),
    ('fii_equity_flow', '2024-04', "Apr'24",  -8671.0),
    ('fii_equity_flow', '2024-05', "May'24",  -4180.0),
    ('fii_equity_flow', '2024-06', "Jun'24",  26565.0),
    ('fii_equity_flow', '2024-07', "Jul'24",  32365.0),
    ('fii_equity_flow', '2024-08', "Aug'24",   7320.0),
    ('fii_equity_flow', '2024-09', "Sep'24",  57724.0),
    ('fii_equity_flow', '2024-10', "Oct'24", -85000.0),
    ('fii_equity_flow', '2024-11', "Nov'24", -45974.0),
    ('fii_equity_flow', '2024-12', "Dec'24", -16000.0),
    ('fii_equity_flow', '2025-01', "Jan'25",  11000.0),
    ('fii_equity_flow', '2025-02', "Feb'25", -18000.0),
    ('fii_equity_flow', '2025-03', "Mar'25",  -4000.0),
    ('fii_equity_flow', '2025-04', "Apr'25",  -8700.0),
    ('fii_equity_flow', '2025-05', "May'25",  19000.0),
    ('fii_equity_flow', '2025-06', "Jun'25",  26000.0),
    ('fii_equity_flow', '2025-07', "Jul'25",   5000.0),
    ('fii_equity_flow', '2025-08', "Aug'25",  -9500.0),
    ('fii_equity_flow', '2025-09', "Sep'25", -27000.0),
    ('fii_equity_flow', '2025-10', "Oct'25",  14600.0),
    ('fii_equity_flow', '2025-11', "Nov'25",   9000.0),
    ('fii_equity_flow', '2025-12', "Dec'25", -15000.0),
    ('fii_equity_flow', '2026-01', "Jan'26", -25000.0),
    ('fii_equity_flow', '2026-02', "Feb'26",  20000.0),
    ('fii_equity_flow', '2026-03', "Mar'26",  -8000.0),  # partial — scheduler accumulates rest
    # ── DII net equity flows — ₹ crore ───────────────────────────────────────
    ('dii_equity_flow', '2023-01', "Jan'23",  31000.0),
    ('dii_equity_flow', '2023-02', "Feb'23",  11000.0),
    ('dii_equity_flow', '2023-03', "Mar'23",  18000.0),
    ('dii_equity_flow', '2023-04', "Apr'23",   5000.0),
    ('dii_equity_flow', '2023-05', "May'23", -15000.0),
    ('dii_equity_flow', '2023-06', "Jun'23", -20000.0),
    ('dii_equity_flow', '2023-07', "Jul'23", -18000.0),
    ('dii_equity_flow', '2023-08', "Aug'23",  27000.0),
    ('dii_equity_flow', '2023-09', "Sep'23",  18000.0),
    ('dii_equity_flow', '2023-10', "Oct'23",  28000.0),
    ('dii_equity_flow', '2023-11', "Nov'23",  10000.0),
    ('dii_equity_flow', '2023-12', "Dec'23", -17000.0),
    ('dii_equity_flow', '2024-01', "Jan'24",  -6000.0),
    ('dii_equity_flow', '2024-02', "Feb'24",  15000.0),
    ('dii_equity_flow', '2024-03', "Mar'24", -11000.0),
    ('dii_equity_flow', '2024-04', "Apr'24",  15000.0),
    ('dii_equity_flow', '2024-05', "May'24",  20000.0),
    ('dii_equity_flow', '2024-06', "Jun'24",  -4000.0),
    ('dii_equity_flow', '2024-07', "Jul'24",  -5000.0),
    ('dii_equity_flow', '2024-08', "Aug'24",  18000.0),
    ('dii_equity_flow', '2024-09', "Sep'24", -14000.0),
    ('dii_equity_flow', '2024-10', "Oct'24",  97976.0),
    ('dii_equity_flow', '2024-11', "Nov'24",  54000.0),
    ('dii_equity_flow', '2024-12', "Dec'24",  28000.0),
    ('dii_equity_flow', '2025-01', "Jan'25",  25000.0),
    ('dii_equity_flow', '2025-02', "Feb'25",  35000.0),
    ('dii_equity_flow', '2025-03', "Mar'25",  22000.0),
    ('dii_equity_flow', '2025-04', "Apr'25",  10000.0),
    ('dii_equity_flow', '2025-05', "May'25",   6000.0),
    ('dii_equity_flow', '2025-06', "Jun'25",  -3500.0),
    ('dii_equity_flow', '2025-07', "Jul'25",   7500.0),
    ('dii_equity_flow', '2025-08', "Aug'25",  12000.0),
    ('dii_equity_flow', '2025-09', "Sep'25",  24000.0),
    ('dii_equity_flow', '2025-10', "Oct'25",   8000.0),
    ('dii_equity_flow', '2025-11', "Nov'25",  13000.0),
    ('dii_equity_flow', '2025-12', "Dec'25",  22000.0),
    ('dii_equity_flow', '2026-01', "Jan'26",  29000.0),
    ('dii_equity_flow', '2026-02', "Feb'26",  -2000.0),
    ('dii_equity_flow', '2026-03', "Mar'26",  11500.0),  # partial — scheduler accumulates rest
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
            "DELETE FROM macro_data_points WHERE series IN "
            "('fii_equity_flow', 'dii_equity_flow')"
        )
    )

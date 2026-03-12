"""Seed us_fed_rate, us_10y_yield, nifty_pe, india_vix historical data into macro_data_points

Revision ID: n1o2p3q4r5s6
Revises: f29c6802b2a8
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'n1o2p3q4r5s6'
down_revision = 'f29c6802b2a8'
branch_labels = None
depends_on = None

# Historical seed data: (series, period, label, value)
_SEED_ROWS = [
    # ── US Fed Funds Rate % (source: FRED FEDFUNDS — fred.stlouisfed.org) ────
    ('us_fed_rate', '2023-01', "Jan'23", 4.33),
    ('us_fed_rate', '2023-02', "Feb'23", 4.57),
    ('us_fed_rate', '2023-03', "Mar'23", 4.79),
    ('us_fed_rate', '2023-04', "Apr'23", 4.83),
    ('us_fed_rate', '2023-05', "May'23", 5.06),
    ('us_fed_rate', '2023-06', "Jun'23", 5.08),
    ('us_fed_rate', '2023-07', "Jul'23", 5.12),
    ('us_fed_rate', '2023-08', "Aug'23", 5.33),
    ('us_fed_rate', '2023-09', "Sep'23", 5.33),
    ('us_fed_rate', '2023-10', "Oct'23", 5.33),
    ('us_fed_rate', '2023-11', "Nov'23", 5.33),
    ('us_fed_rate', '2023-12', "Dec'23", 5.33),
    ('us_fed_rate', '2024-01', "Jan'24", 5.33),
    ('us_fed_rate', '2024-02', "Feb'24", 5.33),
    ('us_fed_rate', '2024-03', "Mar'24", 5.33),
    ('us_fed_rate', '2024-04', "Apr'24", 5.33),
    ('us_fed_rate', '2024-05', "May'24", 5.33),
    ('us_fed_rate', '2024-06', "Jun'24", 5.33),
    ('us_fed_rate', '2024-07', "Jul'24", 5.33),
    ('us_fed_rate', '2024-08', "Aug'24", 5.33),
    ('us_fed_rate', '2024-09', "Sep'24", 5.13),
    ('us_fed_rate', '2024-10', "Oct'24", 4.83),
    ('us_fed_rate', '2024-11', "Nov'24", 4.64),
    ('us_fed_rate', '2024-12', "Dec'24", 4.48),
    ('us_fed_rate', '2025-01', "Jan'25", 4.33),
    ('us_fed_rate', '2025-02', "Feb'25", 4.33),
    ('us_fed_rate', '2025-03', "Mar'25", 4.33),
    ('us_fed_rate', '2025-04', "Apr'25", 4.33),
    ('us_fed_rate', '2025-05', "May'25", 4.33),
    ('us_fed_rate', '2025-06', "Jun'25", 4.33),
    ('us_fed_rate', '2025-07', "Jul'25", 4.08),
    ('us_fed_rate', '2025-08', "Aug'25", 3.83),
    ('us_fed_rate', '2025-09', "Sep'25", 3.83),
    ('us_fed_rate', '2025-10', "Oct'25", 3.58),
    ('us_fed_rate', '2025-11', "Nov'25", 3.33),
    ('us_fed_rate', '2025-12', "Dec'25", 3.33),
    ('us_fed_rate', '2026-01', "Jan'26", 3.33),
    ('us_fed_rate', '2026-02', "Feb'26", 3.33),
    # ── US 10Y Treasury Yield % (source: FRED GS10 — fred.stlouisfed.org) ────
    ('us_10y_yield', '2023-01', "Jan'23", 3.53),
    ('us_10y_yield', '2023-02', "Feb'23", 3.82),
    ('us_10y_yield', '2023-03', "Mar'23", 3.96),
    ('us_10y_yield', '2023-04', "Apr'23", 3.57),
    ('us_10y_yield', '2023-05', "May'23", 3.57),
    ('us_10y_yield', '2023-06', "Jun'23", 3.84),
    ('us_10y_yield', '2023-07', "Jul'23", 3.97),
    ('us_10y_yield', '2023-08', "Aug'23", 4.26),
    ('us_10y_yield', '2023-09', "Sep'23", 4.57),
    ('us_10y_yield', '2023-10', "Oct'23", 4.93),
    ('us_10y_yield', '2023-11', "Nov'23", 4.47),
    ('us_10y_yield', '2023-12', "Dec'23", 4.02),
    ('us_10y_yield', '2024-01', "Jan'24", 4.05),
    ('us_10y_yield', '2024-02', "Feb'24", 4.29),
    ('us_10y_yield', '2024-03', "Mar'24", 4.20),
    ('us_10y_yield', '2024-04', "Apr'24", 4.67),
    ('us_10y_yield', '2024-05', "May'24", 4.49),
    ('us_10y_yield', '2024-06', "Jun'24", 4.36),
    ('us_10y_yield', '2024-07', "Jul'24", 4.26),
    ('us_10y_yield', '2024-08', "Aug'24", 3.94),
    ('us_10y_yield', '2024-09', "Sep'24", 3.65),
    ('us_10y_yield', '2024-10', "Oct'24", 4.06),
    ('us_10y_yield', '2024-11', "Nov'24", 4.42),
    ('us_10y_yield', '2024-12', "Dec'24", 4.25),
    ('us_10y_yield', '2025-01', "Jan'25", 4.69),
    ('us_10y_yield', '2025-02', "Feb'25", 4.51),
    ('us_10y_yield', '2025-03', "Mar'25", 4.27),
    ('us_10y_yield', '2025-04', "Apr'25", 4.29),
    ('us_10y_yield', '2025-05', "May'25", 4.48),
    ('us_10y_yield', '2025-06', "Jun'25", 4.32),
    ('us_10y_yield', '2025-07', "Jul'25", 4.20),
    ('us_10y_yield', '2025-08', "Aug'25", 3.99),
    ('us_10y_yield', '2025-09', "Sep'25", 3.73),
    ('us_10y_yield', '2025-10', "Oct'25", 4.15),
    ('us_10y_yield', '2025-11', "Nov'25", 4.41),
    ('us_10y_yield', '2025-12', "Dec'25", 4.54),
    ('us_10y_yield', '2026-01', "Jan'26", 4.60),
    ('us_10y_yield', '2026-02', "Feb'26", 4.43),
    # ── Nifty 50 P/E Ratio (source: NSE India — nseindia.com) ────────────────
    ('nifty_pe', '2023-01', "Jan'23", 22.5),
    ('nifty_pe', '2023-02', "Feb'23", 21.3),
    ('nifty_pe', '2023-03', "Mar'23", 21.8),
    ('nifty_pe', '2023-04', "Apr'23", 23.6),
    ('nifty_pe', '2023-05', "May'23", 22.3),
    ('nifty_pe', '2023-06', "Jun'23", 23.1),
    ('nifty_pe', '2023-07', "Jul'23", 23.9),
    ('nifty_pe', '2023-08', "Aug'23", 22.2),
    ('nifty_pe', '2023-09', "Sep'23", 23.3),
    ('nifty_pe', '2023-10', "Oct'23", 22.5),
    ('nifty_pe', '2023-11', "Nov'23", 24.6),
    ('nifty_pe', '2023-12', "Dec'23", 24.7),
    ('nifty_pe', '2024-01', "Jan'24", 23.4),
    ('nifty_pe', '2024-02', "Feb'24", 21.6),
    ('nifty_pe', '2024-03', "Mar'24", 22.2),
    ('nifty_pe', '2024-04', "Apr'24", 22.8),
    ('nifty_pe', '2024-05', "May'24", 22.5),
    ('nifty_pe', '2024-06', "Jun'24", 23.1),
    ('nifty_pe', '2024-07', "Jul'24", 24.0),
    ('nifty_pe', '2024-08', "Aug'24", 24.2),
    ('nifty_pe', '2024-09', "Sep'24", 23.5),
    ('nifty_pe', '2024-10', "Oct'24", 22.5),
    ('nifty_pe', '2024-11', "Nov'24", 22.2),
    ('nifty_pe', '2024-12', "Dec'24", 22.4),
    ('nifty_pe', '2025-01', "Jan'25", 21.5),
    ('nifty_pe', '2025-02', "Feb'25", 20.2),
    ('nifty_pe', '2025-03', "Mar'25", 19.8),
    ('nifty_pe', '2025-04', "Apr'25", 21.3),
    ('nifty_pe', '2025-05', "May'25", 21.8),
    ('nifty_pe', '2025-06', "Jun'25", 22.5),
    ('nifty_pe', '2025-07', "Jul'25", 23.1),
    ('nifty_pe', '2025-08', "Aug'25", 22.6),
    ('nifty_pe', '2025-09', "Sep'25", 23.2),
    ('nifty_pe', '2025-10', "Oct'25", 22.8),
    ('nifty_pe', '2025-11', "Nov'25", 21.6),
    ('nifty_pe', '2025-12', "Dec'25", 22.1),
    ('nifty_pe', '2026-01', "Jan'26", 21.9),
    ('nifty_pe', '2026-02', "Feb'26", 20.3),
    # ── India VIX (source: NSE India / Yahoo Finance ^INDIAVIX) ──────────────
    ('india_vix', '2023-01', "Jan'23", 13.82),
    ('india_vix', '2023-02', "Feb'23", 13.25),
    ('india_vix', '2023-03', "Mar'23", 11.59),
    ('india_vix', '2023-04', "Apr'23", 11.68),
    ('india_vix', '2023-05', "May'23", 11.52),
    ('india_vix', '2023-06', "Jun'23", 10.89),
    ('india_vix', '2023-07', "Jul'23", 10.83),
    ('india_vix', '2023-08', "Aug'23", 11.57),
    ('india_vix', '2023-09', "Sep'23", 10.92),
    ('india_vix', '2023-10', "Oct'23", 12.78),
    ('india_vix', '2023-11', "Nov'23", 12.14),
    ('india_vix', '2023-12', "Dec'23", 13.01),
    ('india_vix', '2024-01', "Jan'24", 14.11),
    ('india_vix', '2024-02', "Feb'24", 14.52),
    ('india_vix', '2024-03', "Mar'24", 13.46),
    ('india_vix', '2024-04', "Apr'24", 15.83),
    ('india_vix', '2024-05', "May'24", 20.38),
    ('india_vix', '2024-06', "Jun'24", 14.07),
    ('india_vix', '2024-07', "Jul'24", 14.33),
    ('india_vix', '2024-08', "Aug'24", 15.28),
    ('india_vix', '2024-09', "Sep'24", 13.56),
    ('india_vix', '2024-10', "Oct'24", 14.90),
    ('india_vix', '2024-11', "Nov'24", 15.17),
    ('india_vix', '2024-12', "Dec'24", 14.62),
    ('india_vix', '2025-01', "Jan'25", 16.04),
    ('india_vix', '2025-02', "Feb'25", 15.62),
    ('india_vix', '2025-03', "Mar'25", 14.85),
    ('india_vix', '2025-04', "Apr'25", 17.23),
    ('india_vix', '2025-05', "May'25", 16.44),
    ('india_vix', '2025-06', "Jun'25", 14.18),
    ('india_vix', '2025-07', "Jul'25", 13.72),
    ('india_vix', '2025-08', "Aug'25", 14.39),
    ('india_vix', '2025-09', "Sep'25", 13.15),
    ('india_vix', '2025-10', "Oct'25", 14.86),
    ('india_vix', '2025-11', "Nov'25", 15.33),
    ('india_vix', '2025-12', "Dec'25", 14.27),
    ('india_vix', '2026-01', "Jan'26", 15.81),
    ('india_vix', '2026-02', "Feb'26", 16.44),
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
            "('us_fed_rate', 'us_10y_yield', 'nifty_pe', 'india_vix')"
        )
    )

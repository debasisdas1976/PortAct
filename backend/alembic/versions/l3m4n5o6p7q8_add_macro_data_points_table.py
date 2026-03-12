"""Add macro_data_points table with historical seed data

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'l3m4n5o6p7q8'
down_revision = 'k2l3m4n5o6p7'
branch_labels = None
depends_on = None

# Historical seed data: (series, period, label, value)
_SEED_ROWS = [
    # ── RBI Repo Rate (source: RBI MPC meeting outcomes — rbi.org.in) ─────────
    ('rbi_repo_rate', '2019-01', "Jan'19", 6.50),
    ('rbi_repo_rate', '2019-02', "Feb'19", 6.25),
    ('rbi_repo_rate', '2019-04', "Apr'19", 6.00),
    ('rbi_repo_rate', '2019-06', "Jun'19", 5.75),
    ('rbi_repo_rate', '2019-08', "Aug'19", 5.40),
    ('rbi_repo_rate', '2019-10', "Oct'19", 5.15),
    ('rbi_repo_rate', '2020-03', "Mar'20", 4.40),
    ('rbi_repo_rate', '2020-05', "May'20", 4.00),
    ('rbi_repo_rate', '2022-05', "May'22", 4.40),
    ('rbi_repo_rate', '2022-06', "Jun'22", 4.90),
    ('rbi_repo_rate', '2022-08', "Aug'22", 5.40),
    ('rbi_repo_rate', '2022-09', "Sep'22", 5.90),
    ('rbi_repo_rate', '2022-12', "Dec'22", 6.25),
    ('rbi_repo_rate', '2023-02', "Feb'23", 6.50),
    ('rbi_repo_rate', '2025-02', "Feb'25", 6.25),
    ('rbi_repo_rate', '2025-04', "Apr'25", 6.00),
    ('rbi_repo_rate', '2025-06', "Jun'25", 5.50),  # 50bp cut to 5.50%
    ('rbi_repo_rate', '2025-12', "Dec'25", 5.25),  # 25bp cut to 5.25%
    # ── India CPI YoY % (source: MoSPI — mospi.gov.in) ───────────────────────
    ('india_cpi', '2023-01', "Jan'23", 6.52),
    ('india_cpi', '2023-02', "Feb'23", 6.44),
    ('india_cpi', '2023-03', "Mar'23", 5.66),
    ('india_cpi', '2023-04', "Apr'23", 4.70),
    ('india_cpi', '2023-05', "May'23", 4.25),
    ('india_cpi', '2023-06', "Jun'23", 4.81),
    ('india_cpi', '2023-07', "Jul'23", 7.44),
    ('india_cpi', '2023-08', "Aug'23", 6.83),
    ('india_cpi', '2023-09', "Sep'23", 5.02),
    ('india_cpi', '2023-10', "Oct'23", 4.87),
    ('india_cpi', '2023-11', "Nov'23", 5.55),
    ('india_cpi', '2023-12', "Dec'23", 5.69),
    ('india_cpi', '2024-01', "Jan'24", 5.10),
    ('india_cpi', '2024-02', "Feb'24", 5.09),
    ('india_cpi', '2024-03', "Mar'24", 4.85),
    ('india_cpi', '2024-04', "Apr'24", 4.83),
    ('india_cpi', '2024-05', "May'24", 4.75),
    ('india_cpi', '2024-06', "Jun'24", 5.08),
    ('india_cpi', '2024-07', "Jul'24", 3.54),
    ('india_cpi', '2024-08', "Aug'24", 3.65),
    ('india_cpi', '2024-09', "Sep'24", 5.49),
    ('india_cpi', '2024-10', "Oct'24", 6.21),
    ('india_cpi', '2024-11', "Nov'24", 5.48),
    ('india_cpi', '2024-12', "Dec'24", 5.22),
    ('india_cpi', '2025-01', "Jan'25", 4.26),
    ('india_cpi', '2025-02', "Feb'25", 3.61),
    ('india_cpi', '2025-03', "Mar'25", 3.34),
    ('india_cpi', '2025-04', "Apr'25", 3.16),
    ('india_cpi', '2025-05', "May'25", 3.60),
    ('india_cpi', '2025-06', "Jun'25", 2.10),
    ('india_cpi', '2025-07', "Jul'25", 3.96),
    ('india_cpi', '2025-08', "Aug'25", 3.65),
    ('india_cpi', '2025-09', "Sep'25", 3.73),
    ('india_cpi', '2025-10', "Oct'25", 5.22),
    ('india_cpi', '2025-11', "Nov'25", 3.82),
    ('india_cpi', '2026-01', "Jan'26", 4.31),
    ('india_cpi', '2026-02', "Feb'26", 3.61),
    # ── US CPI YoY % (source: BLS CPIAUCSL — bls.gov) ────────────────────────
    ('us_cpi', '2023-01', "Jan'23", 6.4),
    ('us_cpi', '2023-02', "Feb'23", 6.0),
    ('us_cpi', '2023-03', "Mar'23", 5.0),
    ('us_cpi', '2023-04', "Apr'23", 4.9),
    ('us_cpi', '2023-05', "May'23", 4.0),
    ('us_cpi', '2023-06', "Jun'23", 3.0),
    ('us_cpi', '2023-07', "Jul'23", 3.2),
    ('us_cpi', '2023-08', "Aug'23", 3.7),
    ('us_cpi', '2023-09', "Sep'23", 3.7),
    ('us_cpi', '2023-10', "Oct'23", 3.2),
    ('us_cpi', '2023-11', "Nov'23", 3.1),
    ('us_cpi', '2023-12', "Dec'23", 3.4),
    ('us_cpi', '2024-01', "Jan'24", 3.1),
    ('us_cpi', '2024-02', "Feb'24", 3.2),
    ('us_cpi', '2024-03', "Mar'24", 3.5),
    ('us_cpi', '2024-04', "Apr'24", 3.4),
    ('us_cpi', '2024-05', "May'24", 3.3),
    ('us_cpi', '2024-06', "Jun'24", 3.0),
    ('us_cpi', '2024-07', "Jul'24", 2.9),
    ('us_cpi', '2024-08', "Aug'24", 2.5),
    ('us_cpi', '2024-09', "Sep'24", 2.4),
    ('us_cpi', '2024-10', "Oct'24", 2.6),
    ('us_cpi', '2024-11', "Nov'24", 2.7),
    ('us_cpi', '2024-12', "Dec'24", 2.9),
    ('us_cpi', '2025-01', "Jan'25", 3.0),
    ('us_cpi', '2025-02', "Feb'25", 2.8),
    ('us_cpi', '2025-03', "Mar'25", 2.4),
    ('us_cpi', '2025-04', "Apr'25", 2.3),
    ('us_cpi', '2025-05', "May'25", 2.4),
    ('us_cpi', '2025-06', "Jun'25", 2.7),
    ('us_cpi', '2025-07', "Jul'25", 2.9),
    ('us_cpi', '2025-08', "Aug'25", 2.5),
    ('us_cpi', '2025-09', "Sep'25", 2.4),
    ('us_cpi', '2025-10', "Oct'25", 2.6),
    ('us_cpi', '2025-11', "Nov'25", 2.7),
    ('us_cpi', '2025-12', "Dec'25", 2.9),
    ('us_cpi', '2026-01', "Jan'26", 3.0),
    ('us_cpi', '2026-02', "Feb'26", 2.8),
    # ── US Unemployment % (source: BLS LNS14000000 — bls.gov) ────────────────
    ('us_unemployment', '2023-01', "Jan'23", 3.4),
    ('us_unemployment', '2023-02', "Feb'23", 3.6),
    ('us_unemployment', '2023-03', "Mar'23", 3.5),
    ('us_unemployment', '2023-04', "Apr'23", 3.4),
    ('us_unemployment', '2023-05', "May'23", 3.7),
    ('us_unemployment', '2023-06', "Jun'23", 3.6),
    ('us_unemployment', '2023-07', "Jul'23", 3.5),
    ('us_unemployment', '2023-08', "Aug'23", 3.8),
    ('us_unemployment', '2023-09', "Sep'23", 3.8),
    ('us_unemployment', '2023-10', "Oct'23", 3.9),
    ('us_unemployment', '2023-11', "Nov'23", 3.7),
    ('us_unemployment', '2023-12', "Dec'23", 3.7),
    ('us_unemployment', '2024-01', "Jan'24", 3.7),
    ('us_unemployment', '2024-02', "Feb'24", 3.9),
    ('us_unemployment', '2024-03', "Mar'24", 3.8),
    ('us_unemployment', '2024-04', "Apr'24", 3.9),
    ('us_unemployment', '2024-05', "May'24", 4.0),
    ('us_unemployment', '2024-06', "Jun'24", 4.1),
    ('us_unemployment', '2024-07', "Jul'24", 4.3),
    ('us_unemployment', '2024-08', "Aug'24", 4.2),
    ('us_unemployment', '2024-09', "Sep'24", 4.1),
    ('us_unemployment', '2024-10', "Oct'24", 4.1),
    ('us_unemployment', '2024-11', "Nov'24", 4.2),
    ('us_unemployment', '2024-12', "Dec'24", 4.2),
    ('us_unemployment', '2025-01', "Jan'25", 4.0),
    ('us_unemployment', '2025-02', "Feb'25", 4.1),
    ('us_unemployment', '2025-03', "Mar'25", 4.2),
    ('us_unemployment', '2025-04', "Apr'25", 4.2),
    ('us_unemployment', '2025-05', "May'25", 4.0),
    ('us_unemployment', '2025-06', "Jun'25", 4.1),
    ('us_unemployment', '2025-07', "Jul'25", 4.3),
    ('us_unemployment', '2025-08', "Aug'25", 4.2),
    ('us_unemployment', '2025-09', "Sep'25", 4.1),
    ('us_unemployment', '2025-10', "Oct'25", 4.1),
    ('us_unemployment', '2025-11', "Nov'25", 4.2),
    ('us_unemployment', '2025-12', "Dec'25", 4.2),
    ('us_unemployment', '2026-01', "Jan'26", 4.0),
    ('us_unemployment', '2026-02', "Feb'26", 4.1),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create table only if it doesn't already exist (idempotent for dev environments
    # where create_all may have already created it before the migration ran).
    if 'macro_data_points' not in inspector.get_table_names():
        op.create_table(
            'macro_data_points',
            sa.Column('id',         sa.Integer(),               nullable=False),
            sa.Column('series',     sa.String(50),              nullable=False),
            sa.Column('period',     sa.String(10),              nullable=False),
            sa.Column('label',      sa.String(20),              nullable=False),
            sa.Column('value',      sa.Float(),                 nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('series', 'period', name='uq_macro_series_period'),
        )
        op.create_index('ix_macro_data_points_series', 'macro_data_points', ['series'])

    # Seed historical data — ON CONFLICT DO NOTHING makes this idempotent
    # regardless of whether the table was just created or already existed.
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
    op.drop_index('ix_macro_data_points_series', table_name='macro_data_points')
    op.drop_table('macro_data_points')

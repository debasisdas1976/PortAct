"""Add reference_rates table with current bank FD and govt scheme rates

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'm4n5o6p7q8r9'
down_revision = 'l3m4n5o6p7q8'
branch_labels = None
depends_on = None

# Seed data: (category, name, rate, sub_info)
# Bank FD rates sourced from bankbazaar.com/fixed-deposit-rate.html (March 2026)
# Govt scheme rates sourced from bankbazaar.com/saving-schemes.html (Q4 FY 2025-26)
# Both sets are refreshed automatically by the scheduler — this seed is just the starting point.
_SEED_ROWS = [
    # ── Bank FD rates (general public, best rate p.a.) ─────────────────────
    ('bank_fd', 'sbi',      6.05, 'Best rate p.a.'),
    ('bank_fd', 'hdfc',     6.15, 'Best rate p.a.'),
    ('bank_fd', 'icici',    6.50, 'Best rate p.a.'),
    ('bank_fd', 'axis',     6.45, 'Best rate p.a.'),
    ('bank_fd', 'kotak',    6.25, 'Best rate p.a.'),
    ('bank_fd', 'bob',      6.00, 'Best rate p.a.'),
    ('bank_fd', 'indusind', 6.50, 'Best rate p.a.'),
    ('bank_fd', 'yesbank',  6.75, 'Best rate p.a.'),
    # ── Government savings scheme rates (Q4 FY 2025-26: Jan–Mar 2026) ──────
    ('govt_scheme', 'ppf',      7.10, 'Jan–Mar 2026'),
    ('govt_scheme', 'epf',      8.25, 'FY 2024-25'),   # EPFO annual; updated in scheduler
    ('govt_scheme', 'ssy',      8.20, 'Jan–Mar 2026'),
    ('govt_scheme', 'kvp',      7.50, 'Jan–Mar 2026'),
    ('govt_scheme', 'scss',     8.20, 'Jan–Mar 2026'),
    ('govt_scheme', 'nsc',      7.70, 'Jan–Mar 2026'),
    ('govt_scheme', 'mis',      7.40, 'Jan–Mar 2026'),
    ('govt_scheme', 'rbi_bond', 8.05, 'Jan–Mar 2026'),  # NSC rate + 0.35%
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'reference_rates' not in inspector.get_table_names():
        op.create_table(
            'reference_rates',
            sa.Column('id',         sa.Integer(),               nullable=False),
            sa.Column('category',   sa.String(30),              nullable=False),
            sa.Column('name',       sa.String(50),              nullable=False),
            sa.Column('rate',       sa.Float(),                 nullable=False),
            sa.Column('sub_info',   sa.String(100),             nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                      onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('category', 'name', name='uq_reference_rates_category_name'),
        )
        op.create_index('ix_reference_rates_category', 'reference_rates', ['category'])

    bind.execute(
        sa.text(
            "INSERT INTO reference_rates (category, name, rate, sub_info) "
            "VALUES (:category, :name, :rate, :sub_info) "
            "ON CONFLICT (category, name) DO NOTHING"
        ),
        [
            {"category": cat, "name": name, "rate": rate, "sub_info": sub}
            for cat, name, rate, sub in _SEED_ROWS
        ],
    )


def downgrade() -> None:
    op.drop_index('ix_reference_rates_category', table_name='reference_rates')
    op.drop_table('reference_rates')

"""Add asset_types master table

Revision ID: m9n0o1p2q3r4
Revises: l8m9n0o1p2q3
Create Date: 2026-02-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'm9n0o1p2q3r4'
down_revision = 'l8m9n0o1p2q3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS asset_types (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            display_label VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS ix_asset_types_name ON asset_types (name);
        CREATE INDEX IF NOT EXISTS ix_asset_types_category ON asset_types (category);
    """)

    # Seed all asset types with default categories
    op.execute("""
        INSERT INTO asset_types (name, display_label, category, is_active, sort_order) VALUES
            -- Equity
            ('stock', 'Stock', 'Equity', TRUE, 1),
            ('us_stock', 'US Stock', 'Equity', TRUE, 2),
            ('equity_mutual_fund', 'Equity Mutual Fund', 'Equity', TRUE, 3),
            ('reit', 'REIT', 'Equity', TRUE, 4),
            ('invit', 'InvIT', 'Equity', TRUE, 5),
            -- Fixed Income
            ('debt_mutual_fund', 'Debt Mutual Fund', 'Fixed Income', TRUE, 10),
            ('fixed_deposit', 'Fixed Deposit', 'Fixed Income', TRUE, 11),
            ('recurring_deposit', 'Recurring Deposit', 'Fixed Income', TRUE, 12),
            ('savings_account', 'Savings Account', 'Fixed Income', TRUE, 13),
            ('corporate_bond', 'Corporate Bond', 'Fixed Income', TRUE, 14),
            ('rbi_bond', 'RBI Bond', 'Fixed Income', TRUE, 15),
            ('tax_saving_bond', 'Tax Saving Bond', 'Fixed Income', TRUE, 16),
            -- Govt. Schemes
            ('ppf', 'PPF', 'Govt. Schemes', TRUE, 20),
            ('pf', 'PF', 'Govt. Schemes', TRUE, 21),
            ('nps', 'NPS', 'Govt. Schemes', TRUE, 22),
            ('ssy', 'SSY', 'Govt. Schemes', TRUE, 23),
            ('nsc', 'NSC', 'Govt. Schemes', TRUE, 24),
            ('kvp', 'KVP', 'Govt. Schemes', TRUE, 25),
            ('scss', 'SCSS', 'Govt. Schemes', TRUE, 26),
            ('mis', 'MIS', 'Govt. Schemes', TRUE, 27),
            ('gratuity', 'Gratuity', 'Govt. Schemes', TRUE, 28),
            -- Commodities
            ('commodity', 'Commodity', 'Commodities', TRUE, 30),
            ('sovereign_gold_bond', 'Sovereign Gold Bond', 'Commodities', TRUE, 31),
            -- Crypto
            ('crypto', 'Crypto', 'Crypto', TRUE, 40),
            -- Real Estate
            ('real_estate', 'Real Estate', 'Real Estate', TRUE, 50),
            -- Other
            ('insurance_policy', 'Insurance Policy', 'Other', TRUE, 60),
            ('cash', 'Cash', 'Other', TRUE, 61)
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS asset_types;")

"""Add institutions master table

Revision ID: n0o1p2q3r4s5
Revises: m9n0o1p2q3r4
Create Date: 2026-02-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'n0o1p2q3r4s5'
down_revision = 'm9n0o1p2q3r4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS institutions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            display_label VARCHAR(100) NOT NULL,
            category VARCHAR(30) NOT NULL,
            website VARCHAR(200),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS ix_institutions_name ON institutions (name);
        CREATE INDEX IF NOT EXISTS ix_institutions_category ON institutions (category);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_institutions_name_category
            ON institutions (name, category);
    """)

    # Seed NPS Fund Managers
    op.execute("""
        INSERT INTO institutions (name, display_label, category, sort_order) VALUES
            ('sbi_pension_funds',        'SBI Pension Funds',                'nps_fund_manager', 1),
            ('lic_pension_fund',         'LIC Pension Fund',                 'nps_fund_manager', 2),
            ('uti_retirement',           'UTI Retirement Solutions',         'nps_fund_manager', 3),
            ('icici_prudential_pension', 'ICICI Prudential Pension Fund',    'nps_fund_manager', 4),
            ('hdfc_pension',             'HDFC Pension Management',          'nps_fund_manager', 5),
            ('kotak_pension',            'Kotak Mahindra Pension Fund',      'nps_fund_manager', 6),
            ('aditya_birla_pension',     'Aditya Birla Sun Life Pension',    'nps_fund_manager', 7),
            ('tata_pension',             'Tata Pension Management',          'nps_fund_manager', 8),
            ('axis_pension',             'Axis Pension Fund Management',     'nps_fund_manager', 9),
            ('dsp_pension',              'DSP Pension Fund Managers',        'nps_fund_manager', 10)
        ON CONFLICT (name, category) DO NOTHING;
    """)

    # Seed NPS CRAs
    op.execute("""
        INSERT INTO institutions (name, display_label, category, sort_order) VALUES
            ('protean_cra',  'Protean CRA (formerly NSDL CRA)',    'nps_cra', 1),
            ('kfintech_cra', 'KFintech CRA (formerly Karvy CRA)', 'nps_cra', 2)
        ON CONFLICT (name, category) DO NOTHING;
    """)

    # Seed Insurance Providers
    op.execute("""
        INSERT INTO institutions (name, display_label, category, sort_order) VALUES
            ('lic',                  'LIC',                  'insurance_provider', 1),
            ('sbi_life',             'SBI Life',             'insurance_provider', 2),
            ('hdfc_life',            'HDFC Life',            'insurance_provider', 3),
            ('icici_prudential',     'ICICI Prudential',     'insurance_provider', 4),
            ('max_life',             'Max Life',             'insurance_provider', 5),
            ('bajaj_allianz',        'Bajaj Allianz',        'insurance_provider', 6),
            ('tata_aia',             'Tata AIA',             'insurance_provider', 7),
            ('kotak_life',           'Kotak Life',           'insurance_provider', 8),
            ('star_health',          'Star Health',          'insurance_provider', 9),
            ('niva_bupa',            'Niva Bupa',            'insurance_provider', 10),
            ('care_health',          'Care Health',          'insurance_provider', 11),
            ('aditya_birla_health',  'Aditya Birla Health',  'insurance_provider', 12)
        ON CONFLICT (name, category) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS institutions;")
